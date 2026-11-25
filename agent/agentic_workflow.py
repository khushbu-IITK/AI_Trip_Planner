
from utils.model_loader import ModelLoader
from prompt_library.prompt import SYSTEM_PROMPT
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from tools.weather_info_tool import WeatherInfoTool
from tools.place_search_tool import PlaceSearchTool
from tools.expense_calculator_tool import CalculatorTool
from tools.currency_conversion_tool import CurrencyConverterTool

class GraphBuilder():
    def __init__(self,model_provider: str = "groq"):
        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()
        
        self.tools = []
        
        self.weather_tools = WeatherInfoTool()
        self.place_search_tools = PlaceSearchTool()
        self.calculator_tools = CalculatorTool()
        self.currency_converter_tools = CurrencyConverterTool()
        
        self.tools.extend([* self.weather_tools.weather_tool_list, 
                           * self.place_search_tools.place_search_tool_list,
                           * self.calculator_tools.calculator_tool_list,
                           * self.currency_converter_tools.currency_converter_tool_list])
        
        self.llm_with_tools = self.llm.bind_tools(tools=self.tools)
        
        self.graph = None
        self.checkpointer = MemorySaver()

        self.system_prompt = SYSTEM_PROMPT
    
    
    def agent_function(self,state: MessagesState):
        """Main agent function"""
        user_question = state["messages"]
        input_question = [self.system_prompt] + user_question
        response = self.llm_with_tools.invoke(input_question)
        return {"messages": [response]}
    def build_graph(self):
        graph_builder=StateGraph(MessagesState)
        graph_builder.add_node("agent", self.agent_function)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_edge(START,"agent")
        graph_builder.add_conditional_edges("agent",tools_condition)
        graph_builder.add_edge("tools","agent")
        # No agent -> END edge: tools_condition already routes to END when the
        # model makes no tool call.

        # Conversation memory. The checkpointer saves the full message list after
        # every step, keyed by thread_id. Thread tracking works like this:
        #   1. /plan creates a thread_id (uuid) and returns it to the client.
        #   2. The client keeps it (Streamlit: st.session_state) and sends it
        #      back with every /chat request.
        #   3. Callers pass it as
        #        graph.invoke(input, config={"configurable": {"thread_id": tid}})
        #      and LangGraph loads that thread's history before running.
        # A new trip = a new thread_id. The same thread_id = same conversation.
        # Note: MemorySaver lives in process memory, so history is lost on server
        # restart; swap in a SQLite/Postgres saver to persist it.
        self.graph = graph_builder.compile(checkpointer=self.checkpointer)
        return self.graph
        
    def __call__(self):
        return self.build_graph()