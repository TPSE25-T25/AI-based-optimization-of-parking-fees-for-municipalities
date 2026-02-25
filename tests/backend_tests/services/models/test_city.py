"""Unit tests for City, ParkingZone and PointOfInterest models — thorough + edge cases"""

import pytest
from pydantic import ValidationError
from backend.services.models.city import City, PointOfInterest, ParkingZone


# ── Shared helpers & fixtures ────────────────────────────────────────────────

def _zone(**kw):
    defaults = dict(id=1, name="Lot", current_fee=2.0, position=(0.5, 0.5),
                    maximum_capacity=100, current_capacity=50)
    defaults.update(kw)
    return ParkingZone(**defaults)


def _poi(**kw):
    defaults = dict(id=1, name="POI", position=(0.5, 0.5))
    defaults.update(kw)
    return PointOfInterest(**defaults)


def _city(**kw):
    defaults = dict(id=1, name="C", min_latitude=0.0, max_latitude=1.0,
                    min_longitude=0.0, max_longitude=1.0)
    defaults.update(kw)
    return City(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# PointOfInterest
# ═══════════════════════════════════════════════════════════════════════════════

class TestPointOfInterest:

    def test_valid_creation(self):
        p = _poi()
        assert p.id == 1 and p.name == "POI" and p.position == (0.5, 0.5)

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            _poi(name="")

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PointOfInterest(id=1, name="X")          # no position
        with pytest.raises(ValidationError):
            PointOfInterest(name="X", position=(0, 0))  # no id

    def test_distance_3_4_5(self):
        assert _poi(position=(0.0, 0.0)).distance_to_point((3.0, 4.0)) == 5.0

    def test_distance_to_self(self):
        assert _poi(position=(7.0, 7.0)).distance_to_point((7.0, 7.0)) == 0.0

    def test_distance_negative_coords(self):
        d = _poi(position=(-3.0, -4.0)).distance_to_point((0.0, 0.0))
        assert abs(d - 5.0) < 1e-9


# ═══════════════════════════════════════════════════════════════════════════════
# ParkingZone
# ═══════════════════════════════════════════════════════════════════════════════

class TestParkingZone:

    # ── Construction & defaults ──

    def test_valid_creation(self):
        z = _zone()
        assert z.elasticity == -0.5
        assert z.short_term_share == 0.5
        assert z.min_fee == 0.0 and z.max_fee == 10.0

    def test_string_fee_auto_cast(self):
        assert _zone(current_fee="3.75").current_fee == 3.75

    # ── Field validation ──

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            _zone(name="")

    def test_negative_fee_rejected(self):
        with pytest.raises(ValidationError):
            _zone(current_fee=-1.0)

    def test_zero_fee_allowed(self):
        assert _zone(current_fee=0.0).current_fee == 0.0

    def test_zero_max_capacity_rejected(self):
        with pytest.raises(ValidationError):
            _zone(maximum_capacity=0)

    def test_negative_current_capacity_rejected(self):
        with pytest.raises(ValidationError):
            _zone(current_capacity=-1)

    def test_capacity_exceeds_maximum_rejected(self):
        with pytest.raises(ValidationError):
            _zone(maximum_capacity=10, current_capacity=11)

    def test_capacity_equals_maximum(self):
        assert _zone(maximum_capacity=10, current_capacity=10).is_full()

    def test_positive_elasticity_rejected(self):
        with pytest.raises(ValidationError):
            _zone(elasticity=0.1)

    def test_zero_elasticity_allowed(self):
        assert _zone(elasticity=0).elasticity == 0

    def test_short_term_share_boundaries(self):
        assert _zone(short_term_share=0.0).short_term_share == 0.0
        assert _zone(short_term_share=1.0).short_term_share == 1.0

    def test_short_term_share_out_of_range(self):
        with pytest.raises(ValidationError):
            _zone(short_term_share=1.1)
        with pytest.raises(ValidationError):
            _zone(short_term_share=-0.1)

    def test_negative_min_fee_rejected(self):
        with pytest.raises(ValidationError):
            _zone(min_fee=-1)

    # ── Methods ──

    def test_available_spots(self):
        assert _zone(maximum_capacity=100, current_capacity=30).available_spots() == 70

    def test_available_spots_full(self):
        assert _zone(maximum_capacity=50, current_capacity=50).available_spots() == 0

    def test_available_spots_empty(self):
        assert _zone(maximum_capacity=50, current_capacity=0).available_spots() == 50

    def test_occupancy_rate_values(self):
        assert _zone(maximum_capacity=200, current_capacity=50).occupancy_rate() == 0.25
        assert _zone(maximum_capacity=10, current_capacity=10).occupancy_rate() == 1.0
        assert _zone(maximum_capacity=10, current_capacity=0).occupancy_rate() == 0.0

    def test_is_full(self):
        assert _zone(maximum_capacity=5, current_capacity=5).is_full()
        assert not _zone(maximum_capacity=5, current_capacity=4).is_full()

    def test_can_accommodate(self):
        z = _zone(maximum_capacity=10, current_capacity=8)
        assert z.can_accommodate(2)
        assert not z.can_accommodate(3)

    def test_can_accommodate_default(self):
        assert _zone(maximum_capacity=10, current_capacity=9).can_accommodate()
        assert not _zone(maximum_capacity=10, current_capacity=10).can_accommodate()

    def test_can_accommodate_zero(self):
        assert _zone(maximum_capacity=1, current_capacity=1).can_accommodate(0)

    def test_distance_to_point(self):
        assert _zone(position=(0.0, 0.0)).distance_to_point((3.0, 4.0)) == 5.0

    def test_distance_to_self(self):
        assert _zone(position=(5.0, 5.0)).distance_to_point((5.0, 5.0)) == 0.0

    # ── Edge cases ──

    def test_single_spot_capacity(self):
        z = _zone(maximum_capacity=1, current_capacity=0)
        assert z.available_spots() == 1
        assert z.can_accommodate(1)
        assert not z.can_accommodate(2)

    def test_large_capacity(self):
        z = _zone(maximum_capacity=100_000, current_capacity=99_999)
        assert z.available_spots() == 1
        assert z.occupancy_rate() == pytest.approx(1.0, abs=1e-4)

    def test_json_schema_example_valid(self):
        data = ParkingZone.model_config["json_schema_extra"]["example"]
        z = ParkingZone(**data)
        assert z.name == "CenterLot001"


# ═══════════════════════════════════════════════════════════════════════════════
# City
# ═══════════════════════════════════════════════════════════════════════════════

class TestCity:

    # ── Construction & validation ──

    def test_create_empty(self):
        c = _city()
        assert c.parking_zones == [] and c.point_of_interests == []

    def test_create_with_components(self):
        c = _city(parking_zones=[_zone()], point_of_interests=[_poi()])
        assert len(c.parking_zones) == 1 and len(c.point_of_interests) == 1

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            _city(name="")

    def test_inverted_latitude_rejected(self):
        with pytest.raises(ValidationError):
            _city(min_latitude=50, max_latitude=49)

    def test_inverted_longitude_rejected(self):
        with pytest.raises(ValidationError):
            _city(min_longitude=10, max_longitude=9)

    def test_equal_lat_rejected(self):
        with pytest.raises(ValidationError):
            _city(min_latitude=5, max_latitude=5)

    def test_equal_lon_rejected(self):
        with pytest.raises(ValidationError):
            _city(min_longitude=5, max_longitude=5)

    def test_latitude_out_of_global_range(self):
        with pytest.raises(ValidationError):
            _city(min_latitude=-91)
        with pytest.raises(ValidationError):
            _city(max_latitude=91)

    def test_longitude_out_of_global_range(self):
        with pytest.raises(ValidationError):
            _city(min_longitude=-181)
        with pytest.raises(ValidationError):
            _city(max_longitude=181)

    # ── Position validation at construction ──

    def test_zone_outside_bounds_at_creation(self):
        with pytest.raises(ValidationError):
            _city(parking_zones=[_zone(position=(99.0, 99.0))])

    def test_poi_outside_bounds_at_creation(self):
        with pytest.raises(ValidationError):
            _city(point_of_interests=[_poi(position=(99.0, 99.0))])

    # ── add_parking_zone ──

    def test_add_zone_success(self):
        c = _city()
        c.add_parking_zone(_zone())
        assert len(c.parking_zones) == 1

    def test_add_zone_outside_bounds(self):
        with pytest.raises(ValueError):
            _city().add_parking_zone(_zone(position=(99.0, 99.0)))

    def test_add_zone_duplicate_id(self):
        c = _city(parking_zones=[_zone(id=1)])
        with pytest.raises(ValueError):
            c.add_parking_zone(_zone(id=1, name="Dup"))

    # ── add_point_of_interest ──

    def test_add_poi_success(self):
        c = _city()
        c.add_point_of_interest(_poi())
        assert len(c.point_of_interests) == 1

    def test_add_poi_outside_bounds(self):
        with pytest.raises(ValueError):
            _city().add_point_of_interest(_poi(position=(99.0, 99.0)))

    def test_add_poi_duplicate_id(self):
        c = _city(point_of_interests=[_poi(id=1)])
        with pytest.raises(ValueError):
            c.add_point_of_interest(_poi(id=1, name="Dup"))

    # ── Lookup ──

    def test_get_zone_by_id_found(self):
        z = _zone(id=42)
        c = _city(parking_zones=[z])
        assert c.get_parking_zone_by_id(42) is z

    def test_get_zone_by_id_not_found(self):
        assert _city().get_parking_zone_by_id(999) is None

    # ── Aggregate stats ──

    def test_totals_with_zones(self):
        z1 = _zone(id=1, maximum_capacity=100, current_capacity=80)
        z2 = _zone(id=2, name="B", position=(0.6, 0.6), maximum_capacity=50, current_capacity=50)
        c = _city(parking_zones=[z1, z2])
        assert c.total_parking_capacity() == 150
        assert c.total_occupied_spots() == 130
        assert c.total_available_spots() == 20
        assert c.city_occupancy_rate() == pytest.approx(130 / 150)

    def test_totals_empty_city(self):
        c = _city()
        assert c.total_parking_capacity() == 0
        assert c.total_occupied_spots() == 0
        assert c.total_available_spots() == 0

    def test_occupancy_rate_empty_city(self):
        assert _city().city_occupancy_rate() == 0.0

    # ── Spatial queries ──

    def test_find_nearest_zone(self):
        far = _zone(id=1, name="Far", position=(0.1, 0.1))
        near = _zone(id=2, name="Near", position=(0.5, 0.5))
        c = _city(parking_zones=[far, near])
        assert c.find_nearest_parking_zone((0.5, 0.5)) is near

    def test_find_nearest_zone_empty(self):
        assert _city().find_nearest_parking_zone((0.5, 0.5)) is None

    def test_find_available_zones(self):
        avail = _zone(id=1, maximum_capacity=10, current_capacity=5)
        full = _zone(id=2, name="Full", position=(0.6, 0.6), maximum_capacity=10, current_capacity=10)
        c = _city(parking_zones=[avail, full])
        result = c.find_available_parking_zones()
        assert avail in result and full not in result

    def test_find_available_zones_all_full(self):
        full = _zone(maximum_capacity=10, current_capacity=10)
        assert _city(parking_zones=[full]).find_available_parking_zones() == []

    # ── Edge cases ──

    def test_zone_on_min_boundary(self):
        c = _city(parking_zones=[_zone(position=(0.0, 0.0))])
        assert len(c.parking_zones) == 1

    def test_zone_on_max_boundary(self):
        c = _city(parking_zones=[_zone(position=(1.0, 1.0))])
        assert len(c.parking_zones) == 1

    def test_zone_just_outside_lat(self):
        with pytest.raises(ValidationError):
            _city(parking_zones=[_zone(position=(1.001, 0.5))])

    def test_zone_just_outside_lon(self):
        with pytest.raises(ValidationError):
            _city(parking_zones=[_zone(position=(0.5, -0.001))])

    def test_add_zone_on_boundary(self):
        c = _city()
        c.add_parking_zone(_zone(position=(0.0, 1.0)))
        assert len(c.parking_zones) == 1

    def test_add_poi_on_boundary(self):
        c = _city()
        c.add_point_of_interest(_poi(position=(1.0, 0.0)))
        assert len(c.point_of_interests) == 1

    def test_very_narrow_city(self):
        c = _city(min_latitude=49.0, max_latitude=49.0001,
                  min_longitude=8.0, max_longitude=8.0001)
        assert c.name == "C"
