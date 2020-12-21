from ctypes import Union
from typing import List, Tuple
from django.db import models
from collections.abc import Iterable

from api_fhir_r4.models import FHIRBaseObject


class ContainedResourceConverter:
    """It's used for extracting IMIS Model attributes in FHIR format.

    Methods
    ----------
    convert_from_source(imis_obj: models.Model):
        Convert IMIS Model attribute to FHIR Object
    """

    def __init__(self, imis_resource_name, resource_fhir_converter, resource_extract_method=None):
        """
        Parameters
        ----------
        :param imis_resource_name: Name of attribute, which value should be transformed
        :param resource_fhir_converter: FHIR Converter, it's used for mapping imis resource to fhir representation.
        It must implement at least to_fhir_obj() method
        :param resource_extract_method: Optional argument. Function used for getting attribute value from IMIS Model.
        It has two arguments, first is django model, second one is imis_resource_name.
        Default function is imis_model.__getattribute__(imis_resource_name).
        Return type can be model or iterable (e.g. list of attributes).
        """
        self.imis_resource_name = imis_resource_name
        self.extract_value = resource_extract_method or (lambda model, attribute: model.__getattribute__(attribute))
        self.converter = resource_fhir_converter()

    def convert_from_source(self, imis_obj: models.Model) -> List[FHIRBaseObject]:
        """Convert IMIS Model attribute to FHIR Object

        :param imis_obj: IMIS Object with attribute that have to be converted
        :return: Attribute converted to FHIR object list.
        If attribute is single object then it's still converted to list format.
        """
        resource = self.extract_value(imis_obj, self.imis_resource_name)
        if isinstance(resource, Iterable):
            return self._convert_all_values(list(resource))
        else:
            converted = self._convert_single_resource(resource)
            return [converted] if converted else []

    def _convert_all_values(self, imis_resources: List[object]) -> List[FHIRBaseObject]:
        return [self._convert_single_resource(next_resource) for next_resource in imis_resources]

    def _convert_single_resource(self, imis_resource_value: object) -> FHIRBaseObject:
        if imis_resource_value is not None:
            try:
                fhir_value = self.converter.to_fhir_obj(imis_resource_value)
                return fhir_value
            except Exception as e:
                print("Failed to process: {}".format((self.imis_resource_name, imis_resource_value)))
