def apply_route_rules(architecture, plan: dict, graph) -> None:
    for route in architecture.routes:
        route_name = f"Route:{route.method}:{route.path}"
        graph.add_node(route_name)

        if route.method == "POST" and route.path == "/login" and architecture.auth:
            graph.add_dependency(route_name, "AuthController")
