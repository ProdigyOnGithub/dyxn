from core.config import config
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.vector_store import VectorStoreInterface
from agents.chatbot.chatbot import ChatbotAgent

# Global singletons to prevent re-initialization on every request
_llm = None
_embedding = None
_vector_store = None
_agent = None

def get_llm() -> LLMProviderInterface:
    global _llm
    if _llm is None:
        from core.providers.gemini_provider import GeminiProvider
        _llm = GeminiProvider(api_key=config.GEMINI_API_KEY)
    return _llm

def get_embedding_provider() -> EmbeddingProviderInterface:
    global _embedding
    if _embedding is None:
        from core.providers.sentence_transformer_provider import SentenceTransformerProvider
        _embedding = SentenceTransformerProvider("all-MiniLM-L6-v2")
    return _embedding

def get_vector_store() -> VectorStoreInterface:
    global _vector_store
    if _vector_store is None:
        from db.qdrant_store import QdrantVectorStore
        _vector_store = QdrantVectorStore(config)
    return _vector_store

def get_chatbot_agent() -> ChatbotAgent:
    global _agent
    if _agent is None:
        _agent = ChatbotAgent(
            llm=get_llm(),
            config=config,
            vector_store=get_vector_store(),
            embedding_provider=get_embedding_provider()
        )
    return _agent

# Global orchestrator singleton
_orchestrator = None

def get_workflow_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from agents.latex.planner import PlannerAgent
        from agents.latex.retriever import RetrieverAgent
        from agents.latex.synthesizer import SynthesizerAgent
        from agents.latex.latex_agent import LatexAgent
        from agents.latex.evaluator import EvaluatorAgent
        from agents.latex.orchestrator import WorkflowOrchestrator
        
        llm = get_llm()
        cfg = config
        
        planner = PlannerAgent(llm=llm, config=cfg)
        retriever = RetrieverAgent(llm=llm, config=cfg, vector_store=get_vector_store(), embedding_provider=get_embedding_provider())
        synthesizer = SynthesizerAgent(llm=llm, config=cfg)
        latex_agent = LatexAgent(llm=llm, config=cfg)
        evaluator = EvaluatorAgent(llm=llm, config=cfg)
        
        _orchestrator = WorkflowOrchestrator(
            planner=planner,
            retriever=retriever,
            synthesizer=synthesizer,
            latex_agent=latex_agent,
            evaluator=evaluator
        )
    return _orchestrator
