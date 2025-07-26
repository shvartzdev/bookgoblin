from .start_summary import register_handlers as register_start_summary
from .addmanual import register_handlers as register_addmanual
from .search import register_handlers as register_search


def register_all_handlers(dp):
    register_start_summary(dp)
    register_addmanual(dp)
    register_search(dp)
