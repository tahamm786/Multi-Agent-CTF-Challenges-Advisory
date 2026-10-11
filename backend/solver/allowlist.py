from urllib.parse import urlparse
from .models import AllowedTargetDomain

def get_allowed_domains():
    return list(AllowedTargetDomain.objects.values_list("domain", flat=True))

def is_allowed_target(target_input: str) -> bool:
    try:
        host = urlparse(target_input).netloc or target_input
        host = host.split(":")[0].lower()
        if not host:
            return False
    except Exception:
        return False

    return any(host == d or host.endswith("." + d) for d in get_allowed_domains())