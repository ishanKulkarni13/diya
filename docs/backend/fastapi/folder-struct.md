# Folder structure of the fastAPI backend root folder

    fastapi/
        pyproject.toml
        README.md
        .env.example

        app/
            main.py
            config/
            settings.py
            logging.py
            security.py

            api/
            router.py
            deps.py
            error_handlers.py
            middleware/

            modules/
            auth/
                api.py
                service.py
                repository.py
                schemas.py
                models.py
                policies.py
            users/
                api.py
                service.py
                repository.py
                schemas.py
                models.py
            safety/
                api.py
                service.py
                repository.py
                schemas.py
                models.py
                events.py
            location/
                api.py
                service.py
                repository.py
                schemas.py
                models.py
            devices/
                api.py
                service.py
                repository.py
                schemas.py
                models.py
                events.py
            realtime/
                ws_api.py
                service.py
                stream_manager.py
                schemas.py
            notifications/
                service.py
                providers/
                push_provider.py
                fcm_provider.py
            ai/
                api.py
                service.py
                provider_clients/
                schemas.py
                jobs.py

            shared/
            db/
                base.py
                session.py
            cache/
                redis.py
            queue/
                broker.py
            contracts/
                response.py
                errors.py
                idempotency.py
            observability/
                metrics.py
                tracing.py
            utils/

        migrations/
            versions/

        tests/
            unit/
            integration/
            contract/
            e2e/

        scripts/
            dev/
            ops/

        deployment/
            docker/
            k8s/