# Roadmap for Dyxn moving forward

## Priority 1: Getting MVP up and Running

### Checklist for meeting priority 1:

- [x] **Fixing Auth, Chunk/Embed queue**: Ensuring users can authenticate properly and documents are being transferred from queue to queue for efficient background processing

- [x] **Chatbot Functionality**: Only the latex agent has been built till now, now need to add a chatbot which answers based on context

- [ ] **QoL Changes**: Pretty shitty inefficient code right now, need to make it clean with core.llm and additional changes for proper llm calling, imports, etc (not priority)

- [x] **Frontend**: Have a simple frontend supporting all functionality

- [x] **File Deletion**: Currently the file stays in the system after being processed, need to implement a system which deletes the file after its fully done processing

- [ ] **Latex Endpoint**: Add an endpoint which activates the latex making agent

- [ ] **File Re-Ordering**: Inside agents directory make two directories one for latex maker and another for our chatbot in order to make it easier to scale both their functionalities

- [ ] **Frontend Changes**: Add the progress bar for file loading websocket to frontend or just vibecode a frontend from scratch with good design current one is ass anyways

- [ ] **Final Bug Fixing**: Ensure everything works smoothly and by everything I mean **EVERYTHING** on your local device

- [ ] **Dockerise**: Little bit of tweaking of docker-compose and Dockerfile if needed to wind up