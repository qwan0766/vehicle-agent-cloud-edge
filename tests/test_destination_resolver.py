import unittest

import pytest

from providers.destination_models import DestinationCandidate
from providers.destination_resolver import (
    DestinationClarificationRequired,
    extract_destination_query,
    resolve_destination,
    resolve_destination_detail,
)


class FakeGeocoder:
    provider_name = "fake_geocode"

    def __init__(self):
        self.addresses = []

    def geocode(self, address):
        self.addresses.append(address)

        class Result:
            name = address
            gps = "121.49,31.24"

        return Result()


class LowConfidenceGeocoder:
    provider_name = "fake_geocode"

    def geocode(self, address):
        from providers.amap_geocode_provider import LowConfidenceGeocodeError

        raise LowConfidenceGeocodeError(
            query=address,
            formatted_address="北京东方未来中心",
            gps="116.417,39.915",
            confidence=0.35,
            reason="missing_significant_terms:蔚来中心",
            provider_name=self.provider_name,
        )


class TestDestinationResolver(unittest.TestCase):
    def test_resolves_nio_center_to_gps(self):
        self.assertEqual(resolve_destination("导航去蔚来中心"), "121.50,31.25")

    def test_keeps_explicit_gps(self):
        self.assertEqual(resolve_destination("121.50,31.25"), "121.50,31.25")

    def test_extracts_dynamic_navigation_query(self):
        self.assertEqual(extract_destination_query("导航去外滩"), "外滩")
        self.assertEqual(extract_destination_query("我要去上海虹桥站"), "上海虹桥站")

    def test_uses_geocoder_for_unknown_destination(self):
        result = resolve_destination_detail("导航去外滩", geocoder=FakeGeocoder())

        self.assertEqual(result.name, "外滩")
        self.assertEqual(result.gps, "121.49,31.24")
        self.assertEqual(result.source, "fake_geocode")

    def test_city_qualified_nio_center_uses_full_query_not_builtin_default(self):
        geocoder = FakeGeocoder()

        result = resolve_destination_detail("导航去北京的蔚来中心", geocoder=geocoder)

        self.assertEqual(result.name, "北京蔚来中心")
        self.assertEqual(result.gps, "121.49,31.24")
        self.assertEqual(result.source, "fake_geocode")
        self.assertEqual(geocoder.addresses, ["北京蔚来中心"])

    def test_city_qualified_nio_center_requires_geocoder_instead_of_builtin_default(self):
        with self.assertRaises(ValueError):
            resolve_destination("导航去北京的蔚来中心")

    def test_unknown_destination_requires_geocoder(self):
        with self.assertRaises(ValueError):
            resolve_destination("导航去外滩")

    def test_broad_region_requires_clarification_before_geocoder(self):
        geocoder = FakeGeocoder()

        with self.assertRaises(DestinationClarificationRequired) as context:
            resolve_destination_detail("导航去北京", geocoder=geocoder)

        self.assertEqual(context.exception.query, "北京")
        self.assertEqual(context.exception.reason, "broad_region")
        self.assertEqual(geocoder.addresses, [])

    def test_fictional_or_unclear_place_requires_clarification_before_geocoder(self):
        geocoder = FakeGeocoder()

        with self.assertRaises(DestinationClarificationRequired) as context:
            resolve_destination_detail("导航去高老庄", geocoder=geocoder)

        self.assertEqual(context.exception.query, "高老庄")
        self.assertEqual(context.exception.reason, "unclear_destination")
        self.assertEqual(geocoder.addresses, [])

    def test_unknown_qualifier_for_chain_poi_requires_clarification_before_geocoder(self):
        geocoder = FakeGeocoder()

        with self.assertRaises(DestinationClarificationRequired) as context:
            resolve_destination_detail("导航去霓虹蔚来中心", geocoder=geocoder)

        self.assertEqual(context.exception.query, "霓虹蔚来中心")
        self.assertEqual(context.exception.reason, "unknown_chain_poi_qualifier")
        self.assertEqual(geocoder.addresses, [])


def test_destination_candidate_payload_contract():
    candidate = DestinationCandidate(
        name="北京东方广场蔚来中心",
        gps="116.417,39.915",
        address="北京市东城区东方广场",
        source="amap_geocode",
        confidence=0.91,
        distance_km=12.3,
        reason="provider_candidate",
    )

    assert candidate.to_payload() == {
        "name": "北京东方广场蔚来中心",
        "gps": "116.417,39.915",
        "address": "北京市东城区东方广场",
        "source": "amap_geocode",
        "confidence": 0.91,
        "distance_km": 12.3,
        "reason": "provider_candidate",
    }


def test_low_confidence_geocode_requires_clarification():
    with pytest.raises(DestinationClarificationRequired) as context:
        resolve_destination_detail(
            "导航去北京东方广场蔚来中心",
            geocoder=LowConfidenceGeocoder(),
        )

    assert context.value.reason == "low_confidence_provider_result"
    assert context.value.query == "北京东方广场蔚来中心"
    assert context.value.candidates[0]["name"] == "北京东方未来中心"
    assert context.value.candidates[0]["confidence"] == 0.35


if __name__ == "__main__":
    unittest.main()
