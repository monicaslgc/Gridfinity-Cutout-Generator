from app.services.proposals import generate_proposals
from app.models import ProposalsRequest, Dimensions


def test_generate_proposals_monotonic():
    req = ProposalsRequest(
        item_id="Qtest",
        dims_mm=Dimensions(L=100, W=80, H=30),
        options={}
    )
    res = generate_proposals(req)
    snug = res.proposals[0]
    easy = res.proposals[1]
    assert easy.x_slots >= snug.x_slots
    assert easy.y_slots >= snug.y_slots
    assert easy.z_units >= snug.z_units or easy.z_units == snug.z_units
    assert easy.clearance > snug.clearance


def test_generate_proposals_minimums():
    req = ProposalsRequest(
        item_id="Qtiny",
        dims_mm=Dimensions(L=5, W=5, H=5),
        options={}
    )
    res = generate_proposals(req)
    for p in res.proposals:
        assert p.x_slots >= 1 and p.y_slots >= 1 and p.z_units >= 1
