class TenantRouter:

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "rugby":
            return "rugby"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "rugby":
            return "rugby"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        if {obj1._state.db, obj2._state.db} <= {"default", "rugby"}:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "rugby":
            return db == "rugby"
        return db == "default"