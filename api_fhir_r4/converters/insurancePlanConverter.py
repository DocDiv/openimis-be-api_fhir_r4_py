import core

from django.utils.translation import gettext as _
from location.models import Location
from product.models import Product
from api_fhir_r4.configurations import GeneralConfiguration, R4IdentifierConfig
from api_fhir_r4.converters import BaseFHIRConverter, ReferenceConverterMixin
from fhir.resources.money import Money
from fhir.resources.insuranceplan import InsurancePlan, InsurancePlanCoverage, \
    InsurancePlanCoverageBenefit, InsurancePlanCoverageBenefitLimit, \
    InsurancePlanPlan, InsurancePlanPlanGeneralCost
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.quantity import Quantity
from api_fhir_r4.utils import DbManagerUtils, TimeUtils


class InsurancePlanConverter(BaseFHIRConverter, ReferenceConverterMixin):

    @classmethod
    def to_fhir_obj(cls, imis_product, reference_type=ReferenceConverterMixin.UUID_REFERENCE_TYPE):
        fhir_insurance_plan = InsurancePlan.construct()
        # then create fhir object as usual
        cls.build_fhir_identifiers(fhir_insurance_plan, imis_product)
        cls.build_fhir_pk(fhir_insurance_plan, imis_product.uuid)
        cls.build_fhir_name(fhir_insurance_plan, imis_product)
        cls.build_fhir_type(fhir_insurance_plan, imis_product)
        cls.build_fhir_period(fhir_insurance_plan, imis_product)
        cls.build_fhir_coverage_area(fhir_insurance_plan, imis_product)
        cls.build_fhir_coverage(fhir_insurance_plan, imis_product)
        cls.build_fhir_plan(fhir_insurance_plan, imis_product)
        return fhir_insurance_plan

    @classmethod
    def to_imis_obj(cls, fhir_insurance_plan, audit_user_id):
        errors = []
        fhir_insurance_plan = InsurancePlan(**fhir_insurance_plan)
        imis_product = Product()
        imis_product.uuid = None
        imis_product.audit_user_id = audit_user_id
        cls.check_errors(errors)
        return imis_product

    @classmethod
    def get_reference_obj_id(cls, imis_product):
        return imis_product.uuid

    @classmethod
    def get_fhir_resource_type(cls):
        return InsurancePlan

    @classmethod
    def get_imis_obj_by_fhir_reference(cls, reference, errors=None):
        imis_insurance_uuid = cls.get_resource_id_from_reference(reference)
        return DbManagerUtils.get_object_or_none(Product, uuid=imis_insurance_uuid)

    @classmethod
    def build_fhir_identifiers(cls, fhir_insurance_plan, imis_product):
        identifiers = []
        cls.build_fhir_uuid_identifier(identifiers, imis_product)
        cls.build_fhir_code_identifier(identifiers, imis_product)
        fhir_insurance_plan.identifier = identifiers

    @classmethod
    def build_imis_identifiers(cls, imis_product, fhir_insurance_plan):
        value = cls.get_fhir_identifier_by_code(fhir_insurance_plan.identifier,
                                                R4IdentifierConfig.get_fhir_item_code_type())
        if value:
            imis_product.code = value

    @classmethod
    def get_fhir_code_identifier_type(cls):
        return R4IdentifierConfig.get_fhir_item_code_type()

    @classmethod
    def build_fhir_name(cls, fhir_insurance_plan, imis_product):
        if imis_product.name and imis_product.name != "":
            fhir_insurance_plan.name = imis_product.name

    @classmethod
    def build_imis_name(cls, imis_product, fhir_insurance_plan):
        if fhir_insurance_plan.name and fhir_insurance_plan.name != "":
            imis_product.name = fhir_insurance_plan.name

    @classmethod
    def build_fhir_type(cls, fhir_insurance_plan, imis_product):
        fhir_insurance_plan.type = [cls.__build_insurance_plan_type()]

    @classmethod
    def __build_insurance_plan_type(cls):
        type = cls.build_codeable_concept(
            code="medical",
            system="http://terminology.hl7.org/CodeSystem/insurance-plan-type"
        )
        if len(type.coding) == 1:
            type.coding[0].display = _("Medical")
        return type

    @classmethod
    def build_fhir_period(cls, fhir_insurance_plan, imis_product):
        from core import datetime
        period = Period.construct()
        if imis_product.date_from:
            # check if datetime object
            if isinstance(imis_product.date_from, datetime.datetime):
                period.start = str(imis_product.date_from.date().isoformat())
            else:
                period.start = str(imis_product.date_from.isoformat())
        if imis_product.date_to:
            # check if datetime object
            if isinstance(imis_product.date_to, datetime.datetime):
                period.end = str(imis_product.date_to.date().isoformat())
            else:
                period.end = str(imis_product.date_to.isoformat())
        if period.start or period.end:
            fhir_insurance_plan.period = period

    @classmethod
    def build_imis_period(cls, imis_product, fhir_insurance_plan):
        if fhir_insurance_plan.period:
            period = fhir_insurance_plan.period
            if period.start:
                imis_product.date_from = TimeUtils.str_to_date(period.start)
            if period.end:
                imis_product.date_to = TimeUtils.str_to_date(period.end)

    @classmethod
    def build_fhir_coverage_area(cls, fhir_insurance_plan, imis_product):
        if imis_product.location:
            coverage_area = Reference.construct()
            coverage_area.reference = F"Location/{imis_product.location.uuid}"
            fhir_insurance_plan.coverageArea = [coverage_area]

    @classmethod
    def build_imis_coverage_area(cls, imis_product, fhir_insurance_plan):
        if fhir_insurance_plan.coverageArea:
            coverage_area = fhir_insurance_plan.coverageAreae
            value = cls.__get_location_reference(coverage_area.reference)
            if value:
                imis_product.location = Location.objects.get(uuid=value)

    @classmethod
    def __get_location_reference(cls, location):
        return location.rsplit('/', 1)[1]

    @classmethod
    def build_fhir_coverage(cls, fhir_insurance_plan, imis_product):
        # build coverage
        coverage = InsurancePlanCoverage.construct()
        coverage.type = cls.build_codeable_concept(
            code="medical",
            system="http://terminology.hl7.org/CodeSystem/insurance-plan-type"
        )

        # build coverage benefit
        benefit = InsurancePlanCoverageBenefit.construct()
        benefit.type = cls.build_codeable_concept(
            code="medical",
            system="http://terminology.hl7.org/CodeSystem/insurance-plan-type"
        )
        # build coverage benefit limit slices
        system = f"{GeneralConfiguration.get_system_base_url()}CodeSystem/insurance-plan-coverage-benefit-limit"
        benefit.limit = [
            cls.__build_fhir_limit(
                code="period",
                display=_("Period"),
                system=system,
                unit="month",
                value=imis_product.insurance_period
            )
        ]
        benefit.limit.append(
            cls.__build_fhir_limit(
                code="memberCount",
                display=_("Member Count"),
                system=system,
                unit="member",
                value=imis_product.member_count
            )
        )

        coverage.benefit = [benefit]
        fhir_insurance_plan.coverage = [coverage]

    @classmethod
    def build_imis_coverage(cls, imis_product, fhir_insurance_plan):
        if fhir_insurance_plan.coverage:
            if len(fhir_insurance_plan.coverage) == 1:
                benefit = fhir_insurance_plan.coverage[0].benefit
                cls.__build_imis_limit(imis_product, benefit[0].limit)

    @classmethod
    def __build_fhir_limit(cls, code, display, system, unit, value):
        limit = InsurancePlanCoverageBenefitLimit.construct()
        quantity = Quantity.construct()
        quantity.value = value
        quantity.unit = unit
        limit.value = quantity
        limit.code = cls.build_codeable_concept(code, system)
        limit.code.coding[0].display = _(display)
        return limit

    @classmethod
    def __build_imis_limit(cls, imis_product, benefit_limits):
        for limit in benefit_limits:
            if limit.code.coding[0].code == 'memberCount':
                imis_product.member_count = int(limit.value.value)
            if limit.code.coding[0].code == 'period':
                imis_product.insurance_period = int(limit.value.value)

    @classmethod
    def build_fhir_plan(cls, fhir_insurance_plan, imis_product):
        # get the currency defined in configs from core module
        if hasattr(core, 'currency'):
            currency = core.currency
        else:
            currency = "EUR"

        plan = InsurancePlanPlan.construct()
        # build plan general cost limit slices
        system = f"{GeneralConfiguration.get_system_base_url()}CodeSystem/insurance-plan-general-cost-type"
        plan.generalCost = [
            cls.__build_fhir_general_cost(
                code="lumpsum",
                display=_("Lumpsum"),
                system=system,
                currency=currency,
                value=imis_product.lump_sum
            )
        ]
        if imis_product.threshold:
            plan.generalCost[0].groupSize = imis_product.threshold

        if imis_product.premium_adult:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="premiumAdult",
                    display=_("Premium Adult"),
                    system=system,
                    currency=currency,
                    value=imis_product.premium_adult
                )
           )

        if imis_product.premium_child:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="premiumChild",
                    display=_("Premium Child"),
                    system=system,
                    currency=currency,
                    value=imis_product.premium_child
                )
           )

        if imis_product.registration_lump_sum:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="registrationLumpsum",
                    display=_("Registration Lumpsum"),
                    system=system,
                    currency=currency,
                    value=imis_product.registration_lump_sum
                )
           )

        if imis_product.registration_fee:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="registrationFee",
                    display=_("Registration Fee"),
                    system=system,
                    currency=currency,
                    value=imis_product.registration_fee
                )
           )

        if imis_product.general_assembly_lump_sum:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="generalAssemblyLumpSum",
                    display=_("General Assembly Lumpsum"),
                    system=system,
                    currency=currency,
                    value=imis_product.general_assembly_lump_sum
                )
           )

        if imis_product.general_assembly_fee:
            plan.generalCost.append(
                cls.__build_fhir_general_cost(
                    code="generalAssemblyFee",
                    display=_("General Assembly Fee"),
                    system=system,
                    currency=currency,
                    value=imis_product.general_assembly_fee
                )
           )

        fhir_insurance_plan.plan = [plan]

    @classmethod
    def build_imis_plan(cls, imis_product, fhir_insurance_plan):
        if fhir_insurance_plan.plan:
            if len(fhir_insurance_plan.plan) == 1:
                general_costs = fhir_insurance_plan.plan[0].generalCost
                cls.__build_imis_cost_values(imis_product, general_costs)

    @classmethod
    def __build_fhir_general_cost(cls, code, display, system, currency, value):
        general_cost = InsurancePlanPlanGeneralCost.construct()
        cost = Money.construct()
        cost.value = value
        cost.currency = currency
        general_cost.cost = cost
        general_cost.type = cls.build_codeable_concept(code, system)
        general_cost.type.coding[0].display = _(display)
        return general_cost

    @classmethod
    def __build_imis_cost_values(cls, imis_product, general_costs):
        for cost in general_costs:
            if cost.type.coding[0].code == 'lumpsum':
                imis_product.lump_sum = cost.cost.value
                if cost.groupSize:
                    imis_product.threshold = cost.groupSize
            if cost.type.coding[0].code == 'premiumAdult':
                imis_product.premium_adult = cost.cost.value
            if cost.type.coding[0].code == 'premiumChild':
                imis_product.premium_child = cost.cost.value
            if cost.type.coding[0].code == 'registrationLumpsum':
                imis_product.registration_lump_sum = cost.cost.value
            if cost.type.coding[0].code == 'registrationFee':
                imis_product.registration_fee = cost.cost.value
            if cost.type.coding[0].code == 'generalAssemblyLumpSum':
                imis_product.general_assembly_lump_sum = cost.cost.value
            if cost.type.coding[0].code == 'generalAssemblyFee':
                imis_product.general_assembly_fee = cost.cost.value

    @classmethod
    def build_fhir_extentions(cls, fhir_insurance_plan, imis_product, reference_type):
        pass

    @classmethod
    def build_imis_extentions(cls, imis_product, fhir_insurance_plan):
        pass
