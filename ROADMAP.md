# Roadmap for Dyxn moving forward

## Priority 1: Getting MVP up and Running

### Checklist for meeting priority 1:

- [x] **Fixing Auth, Chunk/Embed queue**: Ensuring users can authenticate properly and documents are being transferred from queue to queue for efficient background processing

- [x] **Chatbot Functionality**: Only the latex agent has been built till now, now need to add a chatbot which answers based on context

- [ ] **QoL Changes**: Pretty shitty inefficient code right now, need to make it clean with core.llm and additional changes for proper llm calling, imports, etc (not priority)

- [x] **Frontend**: Have a simple frontend supporting all functionality

- [x] **File Deletion**: Currently the file stays in the system after being processed, need to implement a system which deletes the file after its fully done processing

- [ ] **Final Bug Fixing**: Ensure everything works smoothly and by everything I mean **EVERYTHING** on your local device

- [ ] **Dockerise**: Little bit of tweaking of docker-compose and Dockerfile if needed to wind up