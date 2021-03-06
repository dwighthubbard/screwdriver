# Events Plugin
> Hapi events plugin for the Screwdriver API

## Usage

```javascript
const Hapi = require('hapi');
const server = new Hapi.Server();
const eventsPlugin = require('./');

server.connection({ port: 3000 });

server.register({
    register: eventsPlugin,
    options: {}
}, () => {
    server.start((err) => {
        if (err) {
            throw err;
        }
        console.log('Server running at:', server.info.uri);
    });
});

```

### Routes

#### Returns a single event
`GET /events/{id}`

#### Returns a list of builds associated with the event
`GET /events/{id}/builds`

### Access to Factory methods
The server supplies factories to plugins in the form of server app values:

```js
// handler eventsPlugin.js
handler: (request, reply) => {
    const factory = request.server.app.eventFactory;

    // ...
}
```
