def apply_model_rules(architecture, plan: dict, graph) -> None:
    for model in architecture.models:
        repository_name = f"{model.name}Repository"
        plan["repositories"].append(repository_name)
        graph.add_node(model.name)
        graph.add_node(repository_name)
        graph.add_node("DatabaseConfig")
        graph.add_dependency(repository_name, "DatabaseConfig")

    for relation in architecture.relations:
        plan["relationships"].append(
            {
                "source": relation.source_model,
                "type": relation.relation_type,
                "target": relation.target_model,
            }
        )
        graph.add_dependency(relation.target_model, relation.source_model)
