# API client

`client.js` contains listing/search and multipart upload requests, JSON error
messages, and network-failure guidance. Requests use relative URLs through the
development proxy. Listing accepts an abort signal; uploads are not auto-retried.
