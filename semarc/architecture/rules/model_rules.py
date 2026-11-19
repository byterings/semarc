def apply_model_rules(architecture, plan: dict, graph, resource_plan: dict) -> None:
    for model in resource_plan["models"]:
        model_name = model["name"]
        repository_name = f"{model_name}Repository"
        service_name = f"{model_name}Service"
        plan["repositories"].append(repository_name)
        for component in [model_name, repository_name, service_name]:
            graph.add_node(component)
        graph.add_dependency(repository_name, "DatabaseConfig")
        graph.add_dependency(repository_name, model_name)
        graph.add_dependency(service_name, repository_name)
        for reference in model["references"]:
            graph.ensure_dependency(service_name, f"{reference['model']}Repository")

    for relation in architecture.relations:
        plan["relationships"].append(
            {
                "source": relation.source_model,
                "type": relation.relation_type,
                "target": relation.target_model,
            }
        )
        if relation.relation_type == "BELONGS_TO":
            graph.ensure_dependency(relation.source_model, relation.target_model)
        else:
            graph.ensure_dependency(relation.target_model, relation.source_model)
