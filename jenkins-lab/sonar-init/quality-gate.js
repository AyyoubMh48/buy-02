// Print only failed gate conditions; never log credentials or arbitrary API bodies.
const fs = require('node:fs');

async function main() {
    const report = ['target/sonar/report-task.txt', '.scannerwork/report-task.txt']
        .find(file => fs.existsSync(file));
    if (!report) throw new Error('No scanner task report available');
    const fields = Object.fromEntries(fs.readFileSync(report, 'utf8').trim().split(/\r?\n/)
        .map(line => { const split = line.indexOf('='); return [line.slice(0, split), line.slice(split + 1)]; }));
    const host = process.env.SONAR_HOST_URL.replace(/\/$/, '');
    const headers = { Authorization: `Bearer ${process.env.SONAR_TOKEN}` };
    async function get(endpoint) {
        const response = await fetch(host + '/api/' + endpoint, { headers, signal: AbortSignal.timeout(15000) });
        if (!response.ok) throw new Error(`SonarQube returned HTTP ${response.status}`);
        return response.json();
    }
    const { task } = await get('ce/task?id=' + encodeURIComponent(fields.ceTaskId));
    if (!task.analysisId) {
        console.log(`SonarQube task status: ${task.status}; no completed analysis to report`);
        return;
    }
    const { projectStatus } = await get('qualitygates/project_status?analysisId=' + encodeURIComponent(task.analysisId));
    console.log(`Quality Gate for ${process.env.SONAR_PROJECT_KEY}: ${projectStatus.status}`);
    for (const condition of projectStatus.conditions || []) {
        if (condition.status === 'ERROR') {
            console.log(`Failed metric ${condition.metricKey}: actual=${condition.actualValue}, comparator=${condition.comparator}, threshold=${condition.errorThreshold}`);
        }
    }
}
main().catch(error => {
    // Network errors can embed request headers: expose only our controlled messages.
    console.error(error.message.startsWith('SonarQube returned HTTP') || error.message === 'No scanner task report available'
        ? error.message : 'Unable to retrieve Quality Gate details');
    process.exitCode = 1;
});
