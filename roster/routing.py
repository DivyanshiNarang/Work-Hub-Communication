from .models import RosterMember

_SENIORITY_RANK = {"junior": 0, "mid": 1, "senior": 2}


def pick_assignee(domain_tags: list[str], complexity: str = "simple") -> RosterMember:
    members = list(RosterMember.objects.all())
    if not members:
        raise ValueError("Roster is empty")

    def overlap(member: RosterMember) -> int:
        return len(set(member.domain_tags) & set(domain_tags))

    best_overlap = max(overlap(m) for m in members)
    if best_overlap == 0:
        raise ValueError(f"No roster member matches domain tags {domain_tags}")

    candidates = [m for m in members if overlap(m) == best_overlap]

    # Complex work goes to the most senior matching person; simple work goes to the least
    # senior, freeing seniors up for the complex work only they're needed for.
    candidates.sort(key=lambda m: _SENIORITY_RANK.get(m.seniority, 0), reverse=complexity == "complex")

    return candidates[0]
