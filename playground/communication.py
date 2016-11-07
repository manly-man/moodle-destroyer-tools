class PreparedMoodleRequest(requests.PreparedRequest):
    def __init__(self):
        super().__init__()
        self.function = None

    def prepare(self, data=None, **kwargs):
        if Jn.ws_function in data:
            self.function = data[Jn.ws_function]
        super().prepare(data=data, **kwargs)

    def prepare_body(self, data, files, json=None):
        super().prepare_body(data, files, json)

    def prepare_url(self, url, params):
        """Prepares the given HTTP URL.
        Mostly copied from requests lib, removed python2 checks and added checks for https"""
        from urllib3.util import parse_url
        from urllib3.exceptions import LocationParseError
        from urllib.parse import urlunparse
        from requests.exceptions import InvalidURL
        from requests.utils import requote_uri

        if isinstance(url, bytes):
            url = url.decode('utf8')
        else:
            url = str(url)

        # Don't do any URL preparation for non-HTTP schemes like `mailto`,
        # `data` etc to work around exceptions from `url_parse`, which
        # handles RFC 3986 only.
        if ':' in url and not url.lower().startswith('http'):
            self.url = url
            return

        # Support for unicode domain names and paths.
        try:
            scheme, auth, host, port, path, query, fragment = parse_url(url)
        except LocationParseError as e:
            raise InvalidURL(*e.args)

        if not scheme:
            # normally an error is thrown, we assume https
            scheme = 'https'
        elif scheme != 'https':
            raise InvalidURL('Invalid URL %r: must be https' % url)

        if not host:
            raise InvalidURL("Invalid URL %r: No host supplied" % url)

        # Only want to apply IDNA to the hostname
        try:
            host = host.encode('idna').decode('utf-8')
        except UnicodeError:
            raise InvalidURL('URL has an invalid label.')

        # Carefully reconstruct the network location
        netloc = auth or ''
        if netloc:
            netloc += '@'
        netloc += host
        if port:
            netloc += ':' + str(port)

        # Bare domains aren't valid URLs.
        if not path:
            path = '/'

        if isinstance(params, (str, bytes)):
            params = requests.utils.to_native_string(params)

        enc_params = self._encode_params(params)
        if enc_params:
            if query:
                query = '%s&%s' % (query, enc_params)
            else:
                query = enc_params

        url = requote_uri(urlunparse([scheme, netloc, path, None, query, fragment]))
        self.url = url


