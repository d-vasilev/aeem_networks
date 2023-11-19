import random
import networkx as nx
import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State

import plotly.graph_objects as go

graph = None


def bg98_bandit(action, prob):
    if prob > 1 or prob < 0:
        raise ValueError("Invalid probability")
    if action == "A":
        return 1
    if action == "B":
        return random.choices([0, 2], [1 - prob, prob])[0]
    raise ValueError("Unknown action")


def train_bandit(prob, graph, node_params, episodes=1000):
    numb_nodes = len(node_params)
    for i in range(numb_nodes):
        graph.nodes[i]["reward"] = {"A": 1, "B": 2 * node_params[i]["1"]}
        graph.nodes[i]["tries"] = {"A": 0, "B": 0}
        graph.nodes[i]["outcomes"] = []
        graph.nodes[i]["actions"] = []
        graph.nodes[i]["probs"] = []

    for _ in range(episodes):
        for i in range(numb_nodes):
            response_type = random.random()
            if response_type < node_params[i]["2"]:
                action = random.choice(["A", "B"])
            else:
                reward = graph.nodes[i]["reward"]
                action = max(reward, key=reward.get)

            graph.nodes[i]["actions"].append(action)
            graph.nodes[i]["outcomes"].append(bg98_bandit(action, prob))

        for i in graph.nodes:
            action = graph.nodes[i]["actions"][-1]
            graph.nodes[i]["tries"][action] = graph.nodes[i]["tries"][action] + 1
            graph.nodes[i]["reward"][action] = (
                graph.nodes[i]["reward"][action]
                + (graph.nodes[i]["outcomes"][-1] - graph.nodes[i]["reward"][action])
                / graph.nodes[i]["tries"][action]
            )

            for j in graph.neighbors(i):
                action = graph.nodes[j]["actions"][-1]
                graph.nodes[i]["tries"][action] = graph.nodes[i]["tries"][action] + 1
                graph.nodes[i]["reward"][action] = (
                    graph.nodes[i]["reward"][action]
                    + (
                        graph.nodes[j]["outcomes"][-1]
                        - graph.nodes[i]["reward"][action]
                    )
                    / graph.nodes[i]["tries"][action]
                )

            graph.nodes[i]["probs"].append(graph.nodes[i]["reward"]["B"] / 2)


def plotly_network(graph):
    pos = nx.spring_layout(graph)

    def create_edge(edge):
        node1, node2, _ = edge

        return go.Scatter(
            x=[pos[node1][0], pos[node2][0]],
            y=[pos[node1][1], pos[node2][1]],
            line=dict(width=1, color="#00ff00"),
            hoverinfo="none",
            mode="lines",
        )

    edge_traces = [create_edge(edge) for edge in nx.to_edgelist(graph)]

    node_x = []
    node_y = []
    node_color = []
    node_text = []
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_color.append("#00ff00")
        node_text.append(node)

    node_trace = go.Scatter(
        name="",
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textfont=dict(family="sans serif", size=12, color="Red"),
        # hoverinfo='text',
        hovertemplate="utility:%{customdata:.2f}",
        marker=dict(
            # showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            reversescale=True,
            color=node_color,
            size=20,
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=10, l=10, r=10, t=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    return fig


def plotly_results(graph):
    data = [
        go.Scatter(
            name=node,
            x=list(range(1000)),
            y=graph.nodes[node]["probs"],
            mode="lines",
        )
        for node in graph.nodes()
    ]

    fig = go.Figure(
        data=data,
        layout=go.Layout(
            margin=dict(b=10, l=10, r=10, t=10),
        ),
    )

    return fig


def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Network Learning"),
            html.H3("Observational Learning Demo"),
            html.Div(
                id="intro",
                children="Explore observational learning simulations. Provide event probabiity, number of nodes, edge forming probability and nodes' parameters.",
            ),
        ],
    )


def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Probability parameter"),
            dcc.Input(id="prob", type="number", min=0, max=1, step=0.1, value=0.5),
            html.Br(),
            html.P("Number of nodes"),
            dcc.Input(id="nodes", type="number", min=1, step=1, value=4),
            html.Br(),
            html.P("Edge's probability"),
            dcc.Input(
                id="prob_edge", type="number", min=0, max=1, step=0.01, value=0.5
            ),
            html.Br(),
            html.P("Nodes parameters"),
            dash.dash_table.DataTable(
                id="nodes_param",
                data=[],
                columns=[
                    {"name": "node", "id": "0"},
                    {
                        "name": "Probability belief",
                        "id": "1",
                        "editable": True,
                        "type": "numeric",
                    },
                    {
                        "name": "Greedy param",
                        "id": "2",
                        "editable": True,
                        "type": "numeric",
                    },
                ],
            ),
            html.Br(),
            html.Button("Run simulation", id="button-run", n_clicks=0),
        ],
    )


def create_net_learn_app(app):
    app.layout = html.Div(
        id="app-container",
        style={"display": "flex"},
        children=[
            html.Div(
                id="left-column",
                style={"width": "30.6666666667%"},
                children=[description_card(), generate_control_card()]
                + [
                    html.Div(
                        ["initial child"],
                        id="output-clientside",
                        style={"display": "none"},
                    )
                ],
            ),
            # Right column
            html.Div(
                id="right-column",
                style={"width": "65.3333333333%"},
                children=[
                    html.Div(
                        children=[
                            html.H5("Network"),
                            dcc.Graph(id="network", style={"height": "250px"}),
                        ],
                    ),
                    html.Div(
                        children=[
                            html.H5("Learning dynamics"),
                            dcc.Graph(id="results", style={"height": "250px"}),
                        ],
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("network", "figure"),
        [
            Input("nodes", "value"),
            Input("prob_edge", "value"),
        ],
    )
    def update_graph_chart(numb_nodes, prob_edge):
        global graph
        graph = nx.gnp_random_graph(numb_nodes, prob_edge)
        return plotly_network(graph)

    @app.callback(
        # Output("network", "figure"),
        Output("results", "figure"),
        [
            Input("button-run", "n_clicks"),
        ],
        [
            State("prob", "value"),
            State("nodes_param", "data"),
            State("results", "figure"),
        ],
    )
    def update_result_chart(n_clicks, prob, node_params, figure):
        if n_clicks > 0:
            train_bandit(prob, graph, node_params, episodes=1000)
            return plotly_results(graph)

        return go.Figure(
            data=go.Scatter(x=[0, 1000], y=[0, 0], mode="lines"),
            layout=go.Layout(
                margin=dict(b=10, l=10, r=10, t=10),
            ),
        )

    @app.callback(
        Output("nodes_param", "data"),
        [
            Input("nodes", "value"),
        ],
        [State("nodes_param", "data")],
    )
    def update_table(numb_nodes, data):
        if numb_nodes == 0:
            return []
        num_rows = len(data)
        if numb_nodes == num_rows:
            return data
        if numb_nodes < num_rows:
            return data[:numb_nodes]
        for x in range(num_rows, numb_nodes):
            data.append({"0": x, "1": 0, "2": 0.05})
        return data


# Run the server
if __name__ == "__main__":
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"}
        ],
    )
    create_net_learn_app(app)
    app.run_server(debug=True)
