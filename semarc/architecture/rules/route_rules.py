def apply_route_rules(architecture, plan: dict, graph, resource_plan: dict) -> None:
    for route in resource_plan["routes"]:
        route_name = f"Route:{route['method']}:{route['path']}"
        graph.add_node(route_name)
        operation = route["operation"]

        if operation["kind"].startswith("auth_"):
            graph.add_dependency(route_name, "AuthController")
        elif operation.get("model"):
            controller = f"{operation['model']}Controller"
            graph.add_node(controller)
            graph.ensure_dependency(controller, f"{operation['model']}Service")
            graph.add_dependency(route_name, controller)

        if route["access"] == "protected":
            graph.add_dependency(route_name, "AuthMiddleware")
