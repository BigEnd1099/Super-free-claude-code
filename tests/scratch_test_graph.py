from api.graph.engine import GraphifyEngine
from pathlib import Path

def test_engine():
    engine = GraphifyEngine(Path("api"), exclude_dirs=["__pycache__"])
    data = engine.scan()
    print(f"Nodes: {len(data['nodes'])}")
    print(f"Edges: {len(data['edges'])}")
    
    from api.graph.report_generator import GraphReportGenerator
    gen = GraphReportGenerator(engine.get_networkx_graph(), Path("api"))
    print(gen.generate())

if __name__ == "__main__":
    test_engine()
