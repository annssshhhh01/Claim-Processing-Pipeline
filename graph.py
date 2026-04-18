from utils import prepare_llm_input,id_agent,classify_pdf_pages,group_pages,discharge_summary_agent,bill_agent,run_agents,aggregate_results
from typing import TypedDict, Dict, List
import fitz
from langgraph.graph import StateGraph
class GraphState(TypedDict):
    pdf_path: str
    doc: object
    classifications: Dict
    grouped: Dict
    id_data: str
    discharge_data: str
    bill_data: str
    final_output: Dict


# 1️⃣ Segregator Node
def segregator_node(state: GraphState):
    pdf_path = state["pdf_path"]

    classifications = classify_pdf_pages(pdf_path)
    grouped = group_pages(classifications)
    doc = fitz.open(pdf_path)

    return {
        "classifications": classifications,
        "grouped": grouped,
        "doc": doc
    }

def id_node(state: GraphState):
    if "identity_document" not in state["grouped"]:
        return {"id_data": {}}

    result = id_agent(state["doc"], state["grouped"]["identity_document"])
    return {"id_data": result}

def discharge_node(state: GraphState):
    if "discharge_summary" not in state["grouped"]:
        return {"discharge_data": {}}

    result = discharge_summary_agent(
        state["doc"], state["grouped"]["discharge_summary"]
    )
    return {"discharge_data": result}

def bill_node(state: GraphState):
    if "itemized_bill" not in state["grouped"]:
        return {"bill_data": {}}

    result = bill_agent(state["doc"], state["grouped"]["itemized_bill"])
    return {"bill_data": result}

def aggregator_node(state: GraphState):
    final = aggregate_results({
        "id_data": state.get("id_data"),
        "discharge_data": state.get("discharge_data"),
        "bill_data": state.get("bill_data")
    })

    state["doc"].close()

    return {"final_output": final}



builder = StateGraph(GraphState)

# add nodes
builder.add_node("segregator", segregator_node)
builder.add_node("id_agent", id_node)
builder.add_node("discharge_agent", discharge_node)
builder.add_node("bill_agent", bill_node)
builder.add_node("aggregator", aggregator_node)

# define flow
builder.set_entry_point("segregator")

builder.add_edge("segregator", "id_agent")
builder.add_edge("id_agent", "discharge_agent")
builder.add_edge("discharge_agent", "bill_agent")
builder.add_edge("bill_agent", "aggregator")


# compile graph
graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({
        "pdf_path": "sample.pdf"
    })

    print("\nFINAL OUTPUT:\n", result["final_output"])