from mesa.examples.basic.boid_flockers.model import BoidFlockers
from mesa.visualization import Slider, SolaraViz, make_space_matplotlib


def boid_draw(agent):
    if not agent.neighbors:  # Only for the first Frame
        neighbors = len(agent.model.space.get_neighbors(agent.pos, agent.vision, False))
    else:
        neighbors = len(agent.neighbors)

    if neighbors <= 1:
        return {"color": "red", "size": 20}
    elif neighbors >= 2:
        return {"color": "green", "size": 20}


model_params = {
    "population": Slider(
        label="Number of boids",
        value=100,
        min=10,
        max=200,
        step=10,
    ),
    "width": 100,
    "height": 100,
    "speed": Slider(
        label="Speed of Boids",
        value=5,
        min=1,
        max=20,
        step=1,
    ),
    "vision": Slider(
        label="Vision of Bird (radius)",
        value=10,
        min=1,
        max=50,
        step=1,
    ),
    "separation": Slider(
        label="Minimum Separation",
        value=2,
        min=1,
        max=20,
        step=1,
    ),
}

model = BoidFlockers()

page = SolaraViz(
    model,
    [make_space_matplotlib(agent_portrayal=boid_draw)],
    model_params=model_params,
    name="Boid Flocking Model",
)
page  # noqa
