
export interface QueryMetric {
    queryid: string;
    query: string;
    calls: number;
    total_time: number;
    mean_time: number;
    rows: number;
    shared_blks_hit?: number;
    shared_blks_read?: number;
}

export function calculateDashboardStats(queries: QueryMetric[]) {
    let totalTime = 0;
    let readCalls = 0;
    let writeCalls = 0;

    // Latency Buckets
    const buckets = { fast: 0, mod: 0, slow: 0, critical: 0 };

    // Table Stats
    const tableStats: Record<string, number> = {};

    queries.forEach(q => {
        totalTime += q.total_time; // Note: API returns total_time, not total_exec_time

        // Load Split
        if (q.query.match(/^select/i)) readCalls += q.calls;
        else if (q.query.match(/^(insert|update|delete)/i)) writeCalls += q.calls;

        // Latency Distribution
        if (q.mean_time < 10) buckets.fast++;
        else if (q.mean_time < 100) buckets.mod++;
        else if (q.mean_time < 1000) buckets.slow++;
        else buckets.critical++;

        // Time Consumed by Table (Simple heuristic)
        // Try to extract table name from FROM/JOIN/UPDATE/INSERT INTO
        // This is a rough heuristic, not a full parser
        const tableMatch = q.query.match(/(?:FROM|JOIN|UPDATE|INSERT\s+INTO)\s+["']?([a-zA-Z0-9_]+)["']?(?:\.["']?([a-zA-Z0-9_]+)["']?)?/i);
        if (tableMatch) {
            // If schema.table, use table name (group 2), else group 1
            const tableName = tableMatch[2] || tableMatch[1];
            if (tableName) {
                tableStats[tableName] = (tableStats[tableName] || 0) + q.total_time;
            }
        }
    });

    // Format Table Stats for Chart
    const topTables = Object.entries(tableStats)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5);

    return {
        totalTime,
        loadSplit: [
            { name: 'Reads', value: readCalls, fill: '#3b82f6' }, // Blue
            { name: 'Writes', value: writeCalls, fill: '#ef4444' } // Red
        ],
        latencyHistogram: [
            { name: '<10ms', count: buckets.fast, fill: '#22c55e', label: 'Fast' }, // Green
            { name: '10-100ms', count: buckets.mod, fill: '#3b82f6', label: 'Moderate' }, // Blue
            { name: '100ms-1s', count: buckets.slow, fill: '#f59e0b', label: 'Slow' }, // Orange
            { name: '>1s', count: buckets.critical, fill: '#ef4444', label: 'Critical' }, // Red
        ],
        timeConsumed: topTables
    };
}
