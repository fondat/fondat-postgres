import pytest
import roax.db as db
import roax.postgresql as postgresql
import roax.resource as r
import roax.schema as s

from datetime import date, datetime
from roax.resource import NotFound
from uuid import uuid4


_schema = s.dict(
    {
        "_id": s.uuid(),
        "_dict": s.dict({"a": s.int()}),
        "_list": s.list(s.int()),
        "_set": s.set(s.str()),
        "_int": s.int(),
        "_float": s.float(),
        "_bool": s.bool(),
        "_bytes": s.bytes(format="binary"),
        "_date": s.date(),
        "_datetime": s.datetime(),
    }
)


@pytest.fixture(scope="module")
def database():
    db = postgresql.Database(minconn=1, maxconn=10, dbname="test")
    with db.cursor() as cursor:
        cursor.execute(
            """
                CREATE TABLE FOO (
                    _id text,
                    _dict jsonb,
                    _list jsonb,
                    _set jsonb,
                    _int integer,
                    _float float,
                    _bool boolean,
                    _bytes bytea,
                    _date date,
                    _datetime timestamp
                );
            """
        )
    yield db
    with db.cursor() as cursor:
        cursor.execute("DROP TABLE FOO;")


@pytest.fixture(scope="module")
def table():
    return postgresql.Table("foo", _schema, "_id")


@pytest.fixture(scope="module")
def resource(database, table):
    return db.TableResource(database, table)


def test_crud(resource):
    body = {
        "_id": uuid4(),
        "_dict": {"a": 1},
        "_list": [1, 2, 3],
        "_set": {"foo", "bar"},
        "_int": 1,
        "_float": 2.3,
        "_bool": True,
        "_bytes": b"12345",
        "_date": s.date().str_decode("2019-01-01"),
        #        "_datetime": s.datetime().str_decode("2019-01-01T01:01:01Z"),
    }
    resource.create(body["_id"], body)
    assert resource.read(body["_id"]) == body
    body["_dict"] = {"a": 2}
    body["_list"] = [2, 3, 4]
    del body["_set"]
    body["_int"] = 2
    body["_float"] = 1.0
    body["_bool"] = False
    del body["_bytes"]
    del body["_date"]
    #   del body["_datetime"]
    resource.update(body["_id"], body)
    assert resource.read(body["_id"]) == body
    resource.delete(body["_id"])
    with pytest.raises(NotFound):
        resource.read(body["_id"])


def test_list(resource):
    count = 10
    for n in range(0, count):
        id = uuid4()
        assert resource.create(id, {"_id": id}) == {"id": id}
    ids = resource.list()
    assert len(ids) == count
    for id in ids:
        resource.delete(id)
    assert len(resource.list()) == 0


def test_list_where(resource):
    for n in range(0, 20):
        id = uuid4()
        assert resource.create(id, {"_id": id, "_int": n}) == {"id": id}
    where = resource.query()
    where.text("_int < ")
    where.param(resource.table.encode("_int", 10))
    ids = resource.list(where=where)
    print(f"ids = {ids}")
    assert len(ids) == 10
    for id in resource.list():
        resource.delete(id)
    assert len(resource.list()) == 0


def test_delete_NotFound(resource):
    with pytest.raises(r.NotFound):
        resource.delete(uuid4())


def test_rollback(resource):
    assert len(resource.list()) == 0
    try:
        with resource.connect():  # transaction demarcation
            id = uuid4()
            resource.create(id, {"_id": id})
            assert len(resource.list()) == 1
            raise RuntimeError  # force rollback
    except RuntimeError:
        pass
    assert len(resource.list()) == 0
