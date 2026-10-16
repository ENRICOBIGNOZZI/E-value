import pytest
from threadpoolctl import threadpool_limits


@pytest.fixture(autouse=True)
def single_thread():
    with threadpool_limits(limits=1):yield
