import mock
from mock import call
from nose.tools import *
from shadow.proxy.web import ProxyConfigError


@raises(ProxyConfigError)
def test_no_true_servers():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()
    app = ProxyFlask(
        svc,
        [],
        ['localhost']
    )


@raises(ProxyConfigError)
def test_no_shadow_servers():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()
    app = ProxyFlask(
        svc,
        ['localhost'],
        [],
    )


@raises(ProxyConfigError)
def test_invalid_results_loggers():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()
    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost'],
        result_loggers=['invalid_results_logger']
    )


@raises(NotImplementedError)
def test_abstract_results_logger():
    from shadow.proxy.web import AbstractResultsLogger
    rs_log = AbstractResultsLogger()
    rs_log.log_result('')


def test_log_result():
    from shadow.proxy.web import ProxyFlask
    from shadow.proxy.web import AbstractResultsLogger
    svc = mock.Mock()

    class MockResultLogger(AbstractResultsLogger):
        pass

    rs_log = MockResultLogger()
    rs_log.log_result = mock.Mock()

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost'],
        result_loggers=[rs_log, rs_log]
    )

    app.log_result('hello')

    assert(rs_log.log_result.called)
    eq_(rs_log.log_result.call_count, 2)
    eq_(rs_log.log_result.call_args_list, [call('hello'), call('hello')])


def test_log_result_no_exceptions():
    from shadow.proxy.web import ProxyFlask
    from shadow.proxy.web import AbstractResultsLogger
    svc = mock.Mock()

    rs_log = mock.Mock(spec=AbstractResultsLogger)
    rs_log.log_result.side_effect = Exception('Test exception')

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost'],
        result_loggers=[rs_log]
    )

    app.log_result('hello')

    assert(rs_log.log_result.called)
    eq_(rs_log.log_result.call_count, 1)
    rs_log.log_result.assert_called_with('hello')


def _mock_response():
    import requests
    import random
    resp = mock.Mock(spec=requests.Response)
    resp.headers = {'header': 'header_value'}
    resp.status_code = {'status_code': random.choice([1337, 7113])}
    resp.text = 'blarblarblar'

    elapsed_time = random.random()
    expected = {
                'headers': resp.headers,
                'status_code': resp.status_code,
                'body': resp.text,
                'elapsed_time': elapsed_time,
                'type': 'http_response'
            }

    return (resp, expected, elapsed_time)


def test_format_response_resp():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost'],
    )

    resp, expected, elapsed_time = _mock_response()

    eq_(app.format_response(resp, elapsed_time=elapsed_time), expected)


def test_format_response_exception():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()

    resp = mock.Mock(spec=Exception)
    resp.message = "Exception Message!!!!!"

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost']
    )
    elapsed_time = 1337.0

    expected = {
                'message': resp.message,
                'repr': repr(resp),
                'elapsed_time': elapsed_time,
                'type': 'exception'
            }

    eq_(app.format_response(resp, elapsed_time=elapsed_time), expected)


def test_format_response_unknown():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()

    resp = mock.Mock()

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost']
    )
    elapsed_time = 1337.0

    expected = {
                'repr': repr(resp),
                'elapsed_time': elapsed_time,
                'type': 'unknown'
            }

    eq_(app.format_response(resp, elapsed_time=elapsed_time), expected)


def test_format_request():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost']
    )

    req, expected = _mock_request()

    eq_(app.format_request(req), expected)


def test_timer_normal():
    from shadow.proxy.web import ProxyFlask
    svc = mock.Mock()

    func = mock.Mock(return_value='meh')

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost']
    )

    result, elapsed = app.timer(func, 'hello', world='lol')

    eq_(result, 'meh')
    func.assert_called_with('hello', world='lol')
    assert elapsed >= 0

    exception = Exception('test')
    func = mock.Mock(side_effect=exception)
    result, elapsed = app.timer(func, 'hello', world='lol')
    eq_(result, exception)
    func.assert_called_with('hello', world='lol')
    assert elapsed >= 0


def _mock_request():
    req = mock.Mock()

    req.path = "/lol"
    req.method = 'MEH'

    req.headers = {
        'header': 'header_value'
    }.items()

    req.args = {
        'get': 'get_value'
    }.items()

    req.form = {
        'post': 'post_value'
    }.items()

    expected = {
        'url': req.path,
        'method': req.method,
        'headers': dict(req.headers),
        'get': dict(req.args),
        'post': dict(req.form)
    }

    return (req, expected)


def test_process_greenlets():
    from shadow.proxy.web import ProxyFlask
    from shadow.proxy.web import AbstractResultsLogger
    import gevent

    svc = mock.Mock()

    mock_result_logger = mock.Mock(spec=AbstractResultsLogger)

    app = ProxyFlask(
        svc,
        ['localhost'],
        ['localhost'],
        result_loggers=[mock_result_logger]
    )

    req, expected_req = _mock_request()

    resp, expected_resp, elapsed_time = _mock_response()
    resp2, expected_resp2, elapsed_time2 = _mock_response()

    ident = lambda x: x

    greenlets = [gevent.spawn(ident, x) for x in [(resp, elapsed_time), (resp2, elapsed_time2)]]

    app.process_greenlets(app.format_request(req), greenlets)

    mock_result_logger.log_result.assert_called_with({
            'request': expected_req,
            'results': [
                expected_resp,
                expected_resp2
            ]
        })


def test_catch_all_default():
    from shadow.proxy.web import ProxyFlask
    from shadow.proxy.web import AbstractResultsLogger
    import shadow.proxy.web
    import gevent

    shadow.proxy.web.config = {
        'safe_mode': True
    }

    svc = gevent

    requests = shadow.proxy.web.requests
    requests.request = mock.Mock()

    resp, expected_resp, elapsed_time = _mock_response()

    req, expected_req = _mock_request()

    shadow.proxy.web.request = req

    requests.request.return_value = resp

    mock_result_logger = mock.Mock(spec=AbstractResultsLogger)

    additional_headers = [('add_header', 'header_value'), ('header', 'altered_header_value')]
    additional_get = [('add_get', 'get_value')]
    additional_post = [('add_post', 'post_value')]

    app = ProxyFlask(
        svc,
        ['true_server'],
        ['shadow_server'],
        shadow_servers_timeout=1337.0,
        true_servers_timeout=1339.0,
        shadow_servers_additional_headers=additional_headers,
        shadow_servers_additional_get_params=additional_get,
        shadow_servers_additional_post_params=additional_post,
        result_loggers=[mock_result_logger]
    )

    path = "/"

    # mock timer to return the randomly generated time
    app.timer = lambda timed_func, *args, **kwargs: (timed_func(*args, **kwargs), elapsed_time)

    app.catch_all(path)

    requests.request.assert_has_calls([call(
        url="true_server/",
        headers=expected_req['headers'],
        data=expected_req['post'],
        params=expected_req['get'],
        timeout=1339.0,
        method=expected_req['method'],
        config=shadow.proxy.web.config
    ), call(
        url="shadow_server/",
        headers=dict(expected_req['headers'].items() + additional_headers),
        data=dict(expected_req['post'].items() + additional_post),
        params=dict(expected_req['get'].items() + additional_get),
        timeout=1337.0,
        method=expected_req['method'],
        config=shadow.proxy.web.config
    )], any_order=True)

    mock_result_logger.log_result.assert_called_with({
            'request': expected_req,
            'results': [
                expected_resp,
                expected_resp
            ]
        })
