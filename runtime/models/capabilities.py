from enum import StrEnum


class Capability(StrEnum):
    REASONING="reasoning"; CODING="coding"; VISION="vision"; TOOL_USE="tool_use"; STREAMING="streaming"; EMBEDDINGS="embeddings"; RERANKING="reranking"; LONG_CONTEXT="long_context"; STRUCTURED_OUTPUT="structured_output"; JSON_OUTPUT="json_output"; IMAGE_GENERATION="image_generation"; SPEECH_TO_TEXT="speech_to_text"; TEXT_TO_SPEECH="text_to_speech"; TRANSLATION="translation"; SUMMARIZATION="summarization"; PLANNING="planning"; RETRIEVAL="retrieval"; CLASSIFICATION="classification"; ANALYSIS="analysis"; FUNCTION_CALLING="function_calling"; CONVERSATION="conversation"
