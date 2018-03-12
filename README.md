## Setting up

Do `docker-compose up` to start the service. The api should be awailable on localhost:8888 after the initialization is complete.
Do `docker-compose down` to destroy the app.


## Endpoints

`GET /orders`: list orders

`POST /orders`: create an order `{"type":"sell", "amount":"5", "price":"2"}`

`DELETE /order/{id}`: delete an order


## Authentication

There are 10 generated users, the service is using Basic HTTP authentication.
Credentials for user `i` are: `{id}:user{id}` (eg. `1:user1` for user 1)

## Tests

Only order book has unit tests. Tests for other components were omitted.

## Resiliency

The implementation is no designed as being production ready. There is no recovery of order book from the database implemented. Do `down` followed by `up` to reset the state.
