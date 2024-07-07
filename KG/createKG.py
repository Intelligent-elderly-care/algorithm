import pandas as pd
from py2neo import Graph, Node, Relationship

# 连接到 Neo4j 数据库
graph = Graph("bolt://localhost:7687", auth=("neo4j", "GJyg6841!"))

# 删除所有节点和关系
graph.run("MATCH (n) DETACH DELETE n")

# 读取 CSV 文件
oldperson_info = pd.read_csv('./oldperson_info.csv')
employee_info = pd.read_csv('./employee_info.csv')
volunteer_info = pd.read_csv('./volunteer_info.csv')
event_info = pd.read_csv('./event_info.csv')

# 创建 OldPerson 节点
for _, row in oldperson_info.iterrows():
    node = Node("OldPerson", id=row['id'], name=row['name'], gender=row['gender'], phone=row['phone'], id_card=row['id_card'], checkin_date=row['checkin_date'], checkout_date=row['checkout_date'], birthday=row['birthday'], imgsetDir=row['imgset_dir'], roomNumber=row['room_number'], firstGuardianName=row['firstguardian_name'], firstGuardianRelationship=row['firstguardian_relationship'], firstGuardianPhone=row['firstguardian_phone'], firstGuardianWechat=row['firstguardian_wechat'], secondGuardianName=row['secondguardian_name'], secondGuardianRelationship=row['secondguardian_relationship'], secondGuardianPhone=row['secondguardian_phone'], secondGuardianWechat=row['secondguardian_wechat'], healthState=row['health_state'], description=row['description'])
    graph.create(node)

# 创建 Employee 节点和关系
for _, row in employee_info.iterrows():
    employee_node = Node("Employee", id=row['id'], name=row['name'], gender=row['gender'], phone=row['phone'], id_card=row['id_card'], birthday=row['birthday'], hire_date=row['hire_date'], resign_date=row['resign_date'], imgsetDir=row['imgset_dir'], description=row['description'])
    graph.create(employee_node)
    
    if not pd.isna(row['oldperson_id']):
        oldperson_node = graph.nodes.match("OldPerson", id=row['id']).first()
        if oldperson_node:
            relationship = Relationship(employee_node, "ASSOCIATES_WITH", oldperson_node)
            graph.create(relationship)
    
    if not pd.isna(row['volunteer_id']):
        volunteer_node = graph.nodes.match("Volunteer", id=row['id']).first()
        if volunteer_node:
            relationship = Relationship(employee_node, "COORDINATES_WITH", volunteer_node)
            graph.create(relationship)

# 创建 Volunteer 节点和关系
for _, row in volunteer_info.iterrows():
    volunteer_node = Node("Volunteer", id=row['id'], name=row['name'], gender=row['gender'], phone=row['phone'], id_card=row['id_card'], birthday=row['birthday'], checkin_date=row['checkin_date'], checkout_date=row['checkout_date'], imgsetDir=row['imgset_dir'], description=row['description'])
    graph.create(volunteer_node)
    
    if not pd.isna(row['oldperson_id']):
        oldperson_node = graph.nodes.match("OldPerson", id=row['id']).first()
        if oldperson_node:
            relationship = Relationship(volunteer_node, "HELPS", oldperson_node)
            graph.create(relationship)

# 定义事件类型映射
event_type_mapping = {
    0: "情感检测",
    1: "义工交互检测",
    2: "陌生人检测",
    3: "摔倒检测",
    4: "禁止闯入",
    5: "危险物品检测"
}

# 创建 Event 节点和关系
for _, row in event_info.iterrows():
    event_type = event_type_mapping[row['event_type']]  # 根据映射字典获取事件类型描述
    event_node = Node("Event", id=row['id'], event_type=event_type, event_date=row['event_date'], event_location=row['event_location'], event_description=row['event_desc'], oldperson_id=row['oldperson_id'])
    graph.create(event_node)
    
    if not pd.isna(row['oldperson_id']):
        oldperson_node = graph.nodes.match("OldPerson", id=row['oldperson_id']).first()
        if oldperson_node:
            relationship = Relationship(event_node, "INVOLVES", oldperson_node)
            graph.create(relationship)
