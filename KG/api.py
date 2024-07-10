from fastapi import FastAPI
from neo4j import GraphDatabase
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

class GraphData(BaseModel):
    nodes: list
    links: list

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 连接到 Neo4j 数据库
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "GJyg6841!"))

@app.get("/api/graph", response_model=GraphData)
async def get_graph():
    session = driver.session()
    result = session.run('MATCH (n)-[r]->(m) RETURN n,r,m')
    
    nodes = []
    links = []
    node_ids = set()  # 用来存储已经添加过的节点 id
    
    for record in result:
        for field in record:
            if hasattr(field, 'labels'):  # 判断是否是节点
                # 只添加未曾添加过的节点 id
                if field.id not in node_ids:
                    nodes.append({
                        'id': field.id,
                        'name': field.get('name', field.get('event_type', '')),
                        'labels': list(field.labels),
                        'properties': dict(field._properties)  # 将节点的属性转换为字典
                    })
                    node_ids.add(field.id)  # 将节点 id 添加到集合中
            elif hasattr(field, 'type'):  # 判断是否是关系
                links.append({
                    'source': field.start_node.id,
                    'target': field.end_node.id,
                    'type': field.type
                })
                
    return {"nodes": nodes, "links": links}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9010)
