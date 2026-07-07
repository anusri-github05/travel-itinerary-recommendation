# 🌍 Travel Itinerary Recommendation System

An AI-powered **Travel Itinerary Recommendation System** that generates personalized travel plans based on a user's destination, trip duration, interests, and budget.

The application leverages **CrewAI** for multi-agent collaboration and **LangGraph** for workflow orchestration, enabling intelligent travel planning, budget validation, itinerary generation, and automatic budget optimization.

---

## Features

- ✈️ Personalized travel itinerary generation
- 💰 Budget feasibility analysis
- 🗺️ Intelligent destination and route planning
- 📅 Day-wise itinerary creation
- 🍽️ Restaurant and attraction recommendations
- 💱 Currency conversion support
- 🌐 Real-time web search integration
- 📊 Expense estimation and cost breakdown
- 🔄 Automatic itinerary revision when budget exceeds limits
- 🤖 Multi-agent AI workflow using CrewAI and LangGraph

---

## Project Workflow

```
                    User Input
                         │
                         ▼
                Budget Reality Check
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Unrealistic Budget           Realistic Budget
          │                             │
          ▼                             ▼
    Budget Recommendation      Destination Planner
                                        │
                                        ▼
                               Local Guide Agent
                                        │
                                        ▼
                              Travel Concierge
                                        │
                              Budget Verification
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
              Within Budget                         Over Budget
                    │                                       │
                    ▼                                       ▼
              Final Itinerary                  Revise Itinerary
                    │                                       │
                    └──────────────► Final Recommendation ◄─┘
```

---

## Technology Stack

### Frontend

- Streamlit

### Backend

- Python

### AI Frameworks

- CrewAI
- LangGraph

### Large Language Models

- Google Gemini
- Groq
- OpenRouter

### Tools

- Web Search Tool
- Currency Converter Tool
- Expense Calculator Tool

---

## Multi-Agent Architecture

### Budget Advisor

- Evaluates whether the user's budget is realistic.
- Suggests a practical budget when necessary.

### Destination Expert

- Plans the most suitable travel route.
- Selects appropriate cities and travel sequence.

### Local Guide

- Generates a detailed day-by-day itinerary.
- Recommends attractions, restaurants, and local experiences.

### Travel Concierge

- Calculates the estimated travel cost.
- Provides the final itinerary with a detailed expense breakdown.

---

## Project Structure

```text
Travel-Itinerary-Recommendation/
│
├── app.py
├── graph_workflow.py
├── llm_config.py
├── requirements.txt
├── README.md
│
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
│
├── tools/
│   ├── search_tool.py
│   ├── expense_tool.py
│   └── currency_tool.py
│
├── .env
└── .gitignore
```

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/travel-itinerary-recommendation.git
cd travel-itinerary-recommendation
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Environment

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file in the project root.

```env
LLM_PROVIDER=gemini

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini/gemini-2.5-flash

GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=groq/llama-3.3-70b-versatile

OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
OPENROUTER_MODEL=openrouter/auto

TAVILY_API_KEY=YOUR_TAVILY_API_KEY
```

---

## Run the Application

```bash
streamlit run app.py
```

---

## Sample Input

**Destination**

```
Goa
```

**Travel Preferences**

```
Beaches, nightlife, seafood, water sports, sightseeing
```

**Trip Duration**

```
5 Days
```

**Budget**

```
₹60,000
```

---

## Sample Output

- Budget feasibility report
- Recommended destinations
- Day-wise itinerary
- Local attraction recommendations
- Restaurant suggestions
- Estimated travel expenses
- Final optimized itinerary

---

## Key Concepts

- Multi-Agent AI Systems
- CrewAI Agents
- LangGraph Workflow Orchestration
- Conditional Routing
- State Management
- Tool Calling
- Prompt Engineering
- LLM-based Planning
- AI-powered Travel Recommendation

---

## Future Enhancements

- Google Maps integration
- Flight booking API
- Hotel booking API
- Weather forecasting
- PDF itinerary generation
- Email sharing
- Voice assistant
- User authentication
- Trip history
- Personalized travel recommendations

---

## Author

**Anusri J R**

Platform Engineer | AI & Data Analytics Enthusiast

---

## License

This project is developed for educational and learning purposes.
