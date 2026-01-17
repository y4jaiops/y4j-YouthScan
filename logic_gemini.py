import google.generativeai as genai
import streamlit as st
import json

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def parse_document_dynamic(file_bytes, target_columns, mime_type="image/jpeg"):
    # Using Gemini 2.5 Flash
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    columns_str = ", ".join(target_columns)
    
    prompt = f"""
    You are an expert OCR assistant for Youth4Jobs. 
    Analyze the provided document. It might contain one candidate or a list (table).
    
    Extract the following information for EACH candidate: {columns_str}.
    
    Rules:
    1. Return ONLY a valid JSON list of objects: [{{...}}, {{...}}].
    2. Even if one candidate, wrap it in a list.
    3. Keys must be exactly: {columns_str}.
    4. If not found, return "".
    5. Translate regional languages to English.
    """
    
    try:
        # Dynamic Mime Type (PDF or Image)
        doc_blob = {"mime_type": mime_type, "data": file_bytes}
        
        result = model.generate_content(
            [prompt, doc_blob],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        parsed = json.loads(result.text)
        if isinstance(parsed, dict):
            return [parsed]
        return parsed
    except Exception as e:
        return [{"error": str(e)}]
