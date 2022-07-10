from peewee import Model

from hyperfocus.database._database import _Database


def test_database_with_models(test_dir):
    test_db_path = test_dir / "test_db.sqlite"
    test_db_path.touch()
    db_test = _Database()

    class TestModel(Model):
        class Meta:
            database = db_test()

    models = [TestModel]
    db_test.connect(test_db_path)

    db_test.init_models(models)

    core_db_test = db_test()
    assert core_db_test.get_tables() == ["testmodel"]
    db_test.close()
    # close method return 'is_open' db status if closed
    assert core_db_test.close() is False
