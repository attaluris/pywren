"""
Tests for lambda only 
"""

import pytest
import time
import boto3 
import uuid
import numpy as np
import time
import pywren
import subprocess
import logging
from six.moves import cPickle as pickle
import unittest
import numpy as np
from flaky import flaky
import sys


lamb = pytest.mark.skipif(
    not pytest.config.getoption("--runlambda", False),
    reason="need --runlambda option to run"
)

class Timeout(unittest.TestCase):

    def setUp(self):
        self.wrenexec = pywren.lambda_executor(job_max_runtime=40)

    @lamb
    def test_simple(self):

        def take_forever():
            time.sleep(45)
            return True

        fut = self.wrenexec.call_async(take_forever, None)
        with pytest.raises(Exception) as execinfo:
            res = fut.result() 
            
    @lamb
    def test_we_dont_raise(self):

        def take_forever():
            time.sleep(45)
            return True

        fut = self.wrenexec.call_async(take_forever, None)
        res = fut.result(throw_except=False)

@lamb            
def test_too_big_runtime():
    """
    Sometimes we accidentally build a runtime that's too big. 
    When this happens, the runtime was leaving behind crap
    and we could never test the runtime again. 
    This tests if we now return a sane exception and can re-run code. 

    There are problems with this test. It is:
    1. lambda only 
    2. depends on lambda having a 512 MB limit. When that is raised someday, 
    this test will always pass. 
    3. Is flaky, because it might be the case that we get _new_
    workers on the next invocation to map that don't have the left-behind
    crap. 
    """


    too_big_config = pywren.wrenconfig.default()
    too_big_config['runtime']['s3_bucket'] = 'pywren-public-us-west-2'
    ver_str = "{}.{}".format(sys.version_info[0], sys.version_info[1])
    too_big_config['runtime']['s3_key'] = "pywren.runtimes/too_big_do_not_use_{}.tar.gz".format(ver_str)


    default_config = pywren.wrenconfig.default()


    wrenexec_toobig = pywren.default_executor(config=too_big_config)
    wrenexec = pywren.default_executor(config=default_config)


    def simple_foo(x):
        return x
    MAP_N = 10

    futures = wrenexec_toobig.map(simple_foo, range(MAP_N))
    for f in futures:
        with pytest.raises(Exception) as excinfo:
            f.result()
        assert excinfo.value.args[1] == 'RUNTIME_TOO_BIG'

    # these ones should work
    futures = wrenexec.map(simple_foo, range(MAP_N))
    for f in futures:
        f.result()

@lamb   
def test_too_big_args():
    """
    This is a test where the data is too large
    to fit on the temporary space on the lambdas. 
    Again, somewhat brittle, lambda specific, and will
    break when they change the available /tmp space limits. 

    Note this test takes a long time because of the large amount of
    data that must be uploaded. 
    """

    wrenexec = pywren.default_executor()

    DATA_MB = 200

    data = "0"*(DATA_MB*1000000)

    def simple_foo(x):
        return 1.0
    
    
    f = wrenexec.call_async(simple_foo, data)
    with pytest.raises(Exception) as excinfo:
        f.result()
    assert excinfo.value.args[1] == 'ARGS_TOO_BIG'

    def simple_foo_2(x):
        #capture data in the closure
        return len(data)

    f = wrenexec.call_async(simple_foo_2, None)
    with pytest.raises(Exception) as excinfo:
        f.result()
    assert excinfo.value.args[1] == 'ARGS_TOO_BIG'
