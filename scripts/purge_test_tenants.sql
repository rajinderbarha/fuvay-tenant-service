-- Purge throwaway test tenants and every row that references them.
--
-- Only 6 tables declare a real FK to `tenants`; the other ~380 carry a bare
-- `tenant_id` column with no constraint, so a plain DELETE FROM tenants would
-- succeed and silently leave orphans everywhere. This walks every table that
-- has a tenant_id column and clears the test ids from each one first.
--
-- DELIBERATELY PRESERVED: "Barha auto store" — the working development
-- tenant, with its 64 service jobs and configured catalogue. It is the dev
-- dataset, not a throwaway test record.

DO $$
DECLARE
    victim_ids UUID[];
    t          RECORD;
    removed    BIGINT;
    total      BIGINT := 0;
BEGIN
    SELECT array_agg(id) INTO victim_ids
    FROM tenants
    WHERE tenant_name IN ('Login E2E Biz', 'Legal Test Services');

    IF victim_ids IS NULL OR array_length(victim_ids, 1) IS NULL THEN
        RAISE NOTICE 'No test tenants matched — nothing to purge.';
        RETURN;
    END IF;

    RAISE NOTICE 'Purging % test tenant(s).', array_length(victim_ids, 1);

    -- Every table with a tenant_id column, except `tenants` itself which is
    -- removed last so the ids stay resolvable while the sweep runs.
    FOR t IN
        SELECT c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables tb
          ON tb.table_name = c.table_name AND tb.table_schema = c.table_schema
        WHERE c.table_schema = 'public'
          AND c.column_name = 'tenant_id'
          AND tb.table_type = 'BASE TABLE'
          AND c.table_name <> 'tenants'
        ORDER BY c.table_name
    LOOP
        EXECUTE format('DELETE FROM %I WHERE tenant_id = ANY($1)', t.table_name)
            USING victim_ids;
        GET DIAGNOSTICS removed = ROW_COUNT;
        IF removed > 0 THEN
            total := total + removed;
            RAISE NOTICE '  %: % row(s)', t.table_name, removed;
        END IF;
    END LOOP;

    -- Users belonging to those tenants.
    DELETE FROM users WHERE tenant_id = ANY(victim_ids);
    GET DIAGNOSTICS removed = ROW_COUNT;
    total := total + removed;
    RAISE NOTICE '  users: % row(s)', removed;

    DELETE FROM tenants WHERE id = ANY(victim_ids);
    GET DIAGNOSTICS removed = ROW_COUNT;
    total := total + removed;
    RAISE NOTICE '  tenants: % row(s)', removed;

    RAISE NOTICE 'Purged % row(s) in total.', total;
END $$;
