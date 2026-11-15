-- Development Supabase only. No application data is read or changed.
BEGIN;
CREATE FUNCTION public.bingo_monitor_health()
RETURNS integer
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $$ SELECT 1; $$;

REVOKE ALL ON FUNCTION public.bingo_monitor_health() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.bingo_monitor_health() FROM authenticated;
REVOKE ALL ON FUNCTION public.bingo_monitor_health() FROM anon;
GRANT EXECUTE ON FUNCTION public.bingo_monitor_health() TO anon;
COMMIT;
