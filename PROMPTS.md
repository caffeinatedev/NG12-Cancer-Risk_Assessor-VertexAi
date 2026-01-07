# PROMPTS.md - NG12 Cancer Risk Assessor

## 1. Executive Summary

This document outlines the prompt engineering strategy for the NG12 Cancer Risk Assessor, a clinical reasoning agent that combines structured patient data with unstructured clinical guidelines using Google Vertex AI Gemini 1.5. The system implements two distinct prompt strategies: one for clinical decision support (Part 1) and another for conversational AI (Part 2), both leveraging the same RAG pipeline.

### Key Design Decisions
- **Grounding First**: All responses must be grounded in NG12 guidelines with specific citations
- **Clinical Safety**: Conservative approach with clear refusal when evidence is insufficient
- **Structured Output**: Consistent formatting for assessments and citations
- **Reusability**: Shared RAG pipeline across both use cases

## 2. Part 1: Clinical Assessment System Prompt

### Tool Use (Function Calling) Strategy
The system uses **Vertex AI Function Calling** to retrieve structured patient data. Instead of injecting patient data directly into the prompt, the agent is initialized with a `get_patient_data` tool.

**Logic Flow:**
1. Agent receives a Patient ID.
2. Agent decides to call `get_patient_data(patient_id)`.
3. System executes the retrieval from `patients.json`.
4. Agent receives the structured data and performs reasoning against NG12 guidelines.

### Primary System Prompt
```
You are a clinical decision support system based on NICE NG12 Cancer Guidelines.
Your role is to assess cancer risk and provide referral recommendations.

CRITICAL INSTRUCTIONS:
1. Base ALL recommendations ONLY on the provided NG12 guideline content
2. Use the available 'get_patient_data' tool to retrieve clinical details for the provided Patient ID before making an assessment.
3. Classify assessment as exactly one of: 'Urgent Referral', 'Urgent Investigation', or 'No Action'
4. Provide clear reasoning citing specific guideline sections
...
```

### Rationale
- **Grounding Enforcement**: Explicit instruction to base responses only on provided context
- **Classification Constraint**: Forces model to choose from predefined categories
- **Citation Requirement**: Ensures all decisions are traceable to guidelines
- **Safety Net**: Clear instruction to default to "No Action" when evidence is insufficient

### Configuration Parameters
- **Model**: Gemini 1.5 Pro / Gemini 2.5 Flash
- **Temperature**: 0.1 (low for clinical consistency)
- **Max Output Tokens**: 2048
- **Top_p**: 0.8
- **Top_k**: 40

## 3. Part 2: Conversational AI System Prompt

### Primary Chat System Prompt
```
You are a clinical guideline assistant based on NICE NG12 Cancer Guidelines.
Your role is to answer questions about cancer referral criteria and guidelines.

CRITICAL INSTRUCTIONS:
1. Answer ONLY based on the provided NG12 guideline content
2. If information is not in the guidelines, state: 'I cannot find support in NG12 for that query'
3. Always include specific page numbers and section references
4. Provide relevant text excerpts from the guidelines
5. Never generate information not present in the provided context

USER QUESTION:
{user_query}

RELEVANT NG12 GUIDELINES:
{guideline_context}

PREVIOUS CONVERSATION:
{conversation_history}

Provide your response with specific NG12 citations:
```

### Multi-turn Context Management
For follow-up questions, the conversation history is formatted as:
```
PREVIOUS CONVERSATION:
User: {previous_question}
Assistant: {previous_response}
User: {current_question}
```

### Rationale
- **Grounding**: Explicit requirement to only use provided context
- **Refusal Strategy**: Clear template for when information is unavailable
- **Citation Requirement**: Ensures all answers include specific references
- **Context Preservation**: Maintains conversation flow while ensuring grounding

## 4. RAG Integration Strategies

### Context Injection Format
The RAG pipeline formats retrieved content as:
```
[Source {index}: NG12 PDF, Page {page_number}, Section: {section_title}]
{content}
```

### Chunk Selection Strategy
- **Top-k Retrieval**: Retrieve top 5-8 most relevant chunks
- **Similarity Threshold**: Filter chunks with similarity score > 0.1
- **Metadata Inclusion**: Include page numbers, section titles, and chunk IDs
- **Content Prioritization**: Prioritize recent and highly relevant content

### Dynamic Context Management
- **Token Budget**: Reserve 1000-1500 tokens for context, rest for response
- **Relevance Scoring**: Use similarity scores to rank and select chunks
- **Metadata Preservation**: Maintain page numbers and section titles for citations

## 5. Grounding and Safety Strategies

### Evidence Verification
- **Citation Mandate**: All claims must include specific NG12 references
- **Excerpt Inclusion**: Include relevant text excerpts to support claims
- **Page Numbering**: Always include specific page numbers for verification

### Refusal Templates
When insufficient evidence is available:
```
I cannot find support in NG12 for that query. No relevant guidelines were found for {specific_query}.
```

### Guardrail Implementation
- **Scope Limitation**: Explicitly limit to NG12 guideline content
- **Medical Disclaimers**: Include appropriate clinical context
- **Evidence Checking**: Verify all responses against retrieved context

## 6. Output Formatting Standards

### Clinical Assessment Format
```
Assessment: {classification}
Reasoning: {detailed_reasoning_based_on_guidelines}
Citations: {list_of_citations_with_page_numbers_and_excerpts}
```

### Chat Response Format
```
{answer_based_on_guidelines}

Citations:
1. Page {page_number}, NG12 PDF: "{relevant_excerpt}"
2. Page {page_number}, NG12 PDF: "{relevant_excerpt}"
```

## 7. Testing and Validation

### Test Cases

#### Clinical Assessment Test
**Input**: Patient with "unexplained hemoptysis"
**Expected**: "Urgent Referral" with lung cancer guideline citations

#### Chat Test
**Input**: "What are the referral criteria for lung cancer?"
**Expected**: Detailed response with specific NG12 citations

### Quality Metrics
- **Grounding Accuracy**: >95% of responses must cite NG12 content
- **Citation Quality**: Citations must match actual guideline content
- **Refusal Rate**: Appropriate refusal when evidence is insufficient
- **Response Consistency**: Similar queries should yield consistent responses

## 8. Production Considerations

### Monitoring Strategies
- **Citation Verification**: Automatically verify citation accuracy
- **Grounding Checks**: Monitor percentage of properly grounded responses
- **Refusal Tracking**: Track and analyze instances where system refuses to answer
- **Performance Metrics**: Monitor response times and token usage

### Security and Compliance
- **Medical Accuracy**: Ensure all responses are clinically appropriate
- **Data Privacy**: No patient data in prompts (only de-identified examples)
- **Regulatory Compliance**: Follow medical AI guidelines and standards

## 9. Iteration and Maintenance

### Prompt Evolution
- **Performance Monitoring**: Track grounding accuracy and citation quality
- **User Feedback**: Incorporate feedback from clinical users
- **Guideline Updates**: Update prompts when NG12 guidelines are revised
- **A/B Testing**: Test prompt variations for improved performance

### Maintenance Procedures
- **Regular Review**: Periodic review of prompt effectiveness
- **Quality Assurance**: Ongoing testing with clinical scenarios
- **Documentation Updates**: Keep PROMPTS.md updated with changes
- **Performance Optimization**: Continuous improvement of token efficiency

## 10. Key Performance Indicators

- **Grounding Rate**: Percentage of responses properly citing NG12 guidelines
- **Citation Accuracy**: Percentage of citations that match actual guideline content
- **Refusal Appropriateness**: Percentage of insufficient evidence cases properly handled
- **Response Relevance**: User satisfaction with response quality and accuracy
- **Token Efficiency**: Average token usage vs. response quality ratio

This prompt engineering strategy ensures that both the clinical decision support system and conversational AI maintain high standards of grounding, safety, and clinical accuracy while providing useful and actionable information to users.