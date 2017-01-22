# Sanic OpenAPI

Adds OpenAPI documentation to a Sanic project

!!! This is still very much a work in progress and may not contain all features in the documentation yet !!!

## Installation

```shell
pip install sanic-openapi
```

Add OpenAPI and Swagger UI:

```python
from sanic_openapi import swagger_blueprint, openapi_blueprint

app.blueprint(openapi_blueprint)
app.blueprint(swagger_blueprint)
```

You'll now have a Swagger UI at the URL `/swagger`.  Your routes will be automatically categorized by their blueprints.

## Usage

### Use simple decorators to document routes:

```python
from sanic_openapi import doc

@app.get("/user/<user_id:int>")
@doc.summary("Fetches a user by ID")
@doc.produces({ "user": { "name": str, "id": int } })
async def get_user(request, user_id):
    return json({ "user": await Users.get(id=user_id) })
```

### Model your input/output

```python
class Car:
    make = str
    model = str
    year = int

class Garage:
    spaces = int
    cars = [Car]

@app.get("/garage")
@doc.summary("Gets the whole garage")
@doc.produces(Garage)
async def get_garage(request):
    return json({
        "spaces": 2,
        "cars": [{"make": "Nissan", "model": "370Z"}]
    })

@app.put("/garage/car")
@doc.summary("Adds a car to the garage")
@doc.consumes({"car": Car})
@doc.produces({"success": bool})
async def test(request):
    cars.append(request.json['car'])
    return json({"success": True})

```

### Get more descriptive

```python
class Car:
    make = doc.String(description="Who made the car")
    model = doc.String(description="Type of car.  This will vary by make")
    year = doc.Integer(description="4-digit year of the car", required=False)

class Garage:
    spaces = doc.Integer(description="How many cars can fit in the garage")
    cars = doc.List(Car, description="All cars in the garage")
```