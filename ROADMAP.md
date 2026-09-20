# leftover work

## actually usable locally

- [x] auth + queue plumbing (auth is parked; uploads still enqueue)
- [x] hook up a real LLM + embedding provider so chat and the graph run
- [x] finish chat route (service exists, route doesn't use it yet)
- [x] worker `__main__` so chunk/embed processes actually start
- [ ] go through the remaining import/config bugs on a real machine
- [ ] docker compose / Dockerfile once the python side isn't lying about paths

## beyond mvp
- [ ] add graph based reasoning using neo4j
- [ ] ~~implement Ray Serve which essentially works like Kubernetes but for models, helps with auto scaling~~
Reason: Ray comes with dashboards and other extra stuff that takes up like 2gb extra of RAM which is not feasible for our scale.
- [ ] since ingestion is done on the fly, make it respond with "not enough info" if files havent been processed yet
- [] Add an alternate TOC based chunking and retrieval system 