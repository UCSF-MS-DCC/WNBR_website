// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', () => {
    const DATA_URL = '/static/data/wnbr_dash_source_data_07182025_complete.csv';

    let rawData = [];
    let charts = {};

    const chartConfigs = {
        monthlyVisits: {
            ctx: document.getElementById('monthly-visits-chart').getContext('2d'),
            type: 'line',
            options: {
                responsive: true,
                plugins: { legend: { display: false }, title: { display: true, text: 'Monthly Participant Visits' } },
                scales: { x: { title: { display: true, text: 'Date' } }, y: { title: { display: true, text: 'Number of Visits' } } }
            }
        },
        collectionTypes: {
            ctx: document.getElementById('collection-types-chart').getContext('2d'),
            type: 'doughnut',
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' }, title: { display: true, text: 'Distribution of Data Collection Types' } }
            }
        },
        sex: {
            ctx: document.getElementById('sex-chart').getContext('2d'),
            type: 'pie',
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' }, title: { display: true, text: 'Distribution by Sex' } }
            }
        },
        race: {
            ctx: document.getElementById('race-chart').getContext('2d'),
            type: 'bar',
            options: {
                responsive: true,
                plugins: { legend: { display: false }, title: { display: true, text: 'Distribution by Race' } },
                scales: { x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } } }
            }
        },
        ethnicity: {
            ctx: document.getElementById('ethnicity-chart').getContext('2d'),
            type: 'bar',
            options: {
                responsive: true,
                plugins: { legend: { display: false }, title: { display: true, text: 'Distribution by Ethnicity' } },
                 scales: { x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } } }
            }
        },
        sampleAvailability: {
            ctx: document.getElementById('sample-availability-chart').getContext('2d'),
            type: 'bar',
            options: {
                responsive: true,
                plugins: { legend: { display: false }, title: { display: true, text: 'Patients with Available Samples by Type' } },
                scales: { y: { title: { display: true, text: 'Number of Patients' } } }
            }
        },
        clinicParticipants: {
            ctx: document.getElementById('clinic-participants-chart').getContext('2d'),
            type: 'bar',
            options: {
                responsive: true,
                plugins: { legend: { display: false }, title: { display: true, text: 'Participants per Referring Clinic' } }
            }
        }
    };

    // Color palettes for charts
    const COLORS = [
        '#36A2EB', '#FF6384', '#4BC0C0', '#FF9F40', '#9966FF', '#FFCD56', '#C9CBCF'
    ];
    const COLORS_BORDER = COLORS.map(c => c + 'B3'); // Add transparency

    // Fetch and parse data
    Papa.parse(DATA_URL, {
        download: true,
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
            rawData = results.data;
            // Convert collection_date to Date objects
            rawData.forEach(d => {
                d.collection_date = new Date(d.collection_date);
            });
            initializeDashboard();
        }
    });

    function initializeDashboard() {
        populateFilters();
        updateDashboard();
        document.querySelectorAll('.filter-dropdown').forEach(el => {
            el.addEventListener('change', updateDashboard);
        });
    }

    function populateFilters() {
        const filters = {
            'clinic-filter': [...new Set(rawData.map(d => d.referring_clinic))],
            'sex-filter': [...new Set(rawData.map(d => d.sex))],
            'race-filter': [...new Set(rawData.map(d => d.race))],
            'ethnicity-filter': [...new Set(rawData.map(d => d.ethnicity))]
        };

        for (const [id, options] of Object.entries(filters)) {
            const select = document.getElementById(id);
            select.innerHTML = '<option value="all">All</option>'; // Reset
            options.sort().forEach(opt => {
                select.innerHTML += `<option value="${opt}">${opt}</option>`;
            });
        }
    }

    function getFilteredData() {
        const clinic = document.getElementById('clinic-filter').value;
        const sex = document.getElementById('sex-filter').value;
        const race = document.getElementById('race-filter').value;
        const ethnicity = document.getElementById('ethnicity-filter').value;

        return rawData.filter(d =>
            (clinic === 'all' || d.referring_clinic === clinic) &&
            (sex === 'all' || d.sex === sex) &&
            (race === 'all' || d.race === race) &&
            (ethnicity === 'all' || d.ethnicity === ethnicity)
        );
    }

    function updateDashboard() {
        const data = getFilteredData();

        updateKPIs(data);

        // Destroy old charts before creating new ones
        Object.values(charts).forEach(chart => chart.destroy());

        updateMonthlyVisits(data);
        updateCollectionTypes(data);
        updateDemographics(data, 'sex', 'sex-chart');
        updateDemographics(data, 'race', 'race-chart');
        updateDemographics(data, 'ethnicity', 'ethnicity-chart');
        updateSampleAvailability(data);
        updateClinicParticipants(data);
    }

    function updateKPIs(data) {
        const uniqueParticipants = new Set(data.map(d => d.weill_id));
        const sampleCols = ['serum', 'plasma', 'lymphocyte', 'CSF-supernate', 'CSF-pellet', 'dna'];
        const patientsWithSamples = new Set();
        data.forEach(d => {
            if (sampleCols.some(col => d[col] === 'Yes')) {
                patientsWithSamples.add(d.weill_id);
            }
        });
        const uniqueClinics = new Set(data.map(d => d.referring_clinic));

        document.getElementById('total-participants').textContent = uniqueParticipants.size;
        document.getElementById('total-patients-with-samples').textContent = patientsWithSamples.size;
        document.getElementById('total-clinics').textContent = uniqueClinics.size;
    }

    function processCount(data, key) {
        const counts = data.reduce((acc, curr) => {
            acc[curr[key]] = (acc[curr[key]] || 0) + 1;
            return acc;
        }, {});
        return Object.entries(counts).sort((a, b) => b[1] - a[1]);
    }

    function updateMonthlyVisits(data) {
        const visits = data.reduce((acc, { collection_date }) => {
            const month = `${collection_date.getFullYear()}-${String(collection_date.getMonth() + 1).padStart(2, '0')}`;
            acc[month] = (acc[month] || 0) + 1;
            return acc;
        }, {});
        const sortedMonths = Object.keys(visits).sort();
        const chartData = {
            labels: sortedMonths,
            datasets: [{ data: sortedMonths.map(m => visits[m]), fill: false, borderColor: '#0078e7', tension: 0.1 }]
        };
        charts.monthlyVisits = new Chart(chartConfigs.monthlyVisits.ctx, { ...chartConfigs.monthlyVisits, data: chartData });
    }

    function updateCollectionTypes(data) {
        const counts = processCount(data, 'wnbr_data');
        const chartData = {
            labels: counts.map(d => d[0]),
            datasets: [{ data: counts.map(d => d[1]), backgroundColor: COLORS, borderColor: COLORS_BORDER, borderWidth: 1 }]
        };
        charts.collectionTypes = new Chart(chartConfigs.collectionTypes.ctx, { ...chartConfigs.collectionTypes, data: chartData });
    }

    function updateDemographics(data, key, chartId) {
        const counts = processCount(data, key);
        const config = chartConfigs[key];
        const chartData = {
            labels: counts.map(d => d[0]),
            datasets: [{ data: counts.map(d => d[1]), backgroundColor: COLORS, borderColor: COLORS_BORDER, borderWidth: 1 }]
        };
        charts[key] = new Chart(config.ctx, { ...config, data: chartData });
    }

    function updateSampleAvailability(data) {
        const sampleCols = ['serum', 'plasma', 'lymphocyte', 'CSF-supernate', 'CSF-pellet', 'dna'];
        const counts = {};
        sampleCols.forEach(col => {
            const patientSet = new Set(data.filter(d => d[col] === 'Yes').map(d => d.weill_id));
            counts[col] = patientSet.size;
        });
        const sortedCounts = Object.entries(counts).sort((a,b) => b[1] - a[1]);

        const chartData = {
            labels: sortedCounts.map(d => d[0]),
            datasets: [{ data: sortedCounts.map(d => d[1]), backgroundColor: COLORS, borderColor: COLORS_BORDER, borderWidth: 1 }]
        };
        charts.sampleAvailability = new Chart(chartConfigs.sampleAvailability.ctx, { ...chartConfigs.sampleAvailability, data: chartData });
    }

    function updateClinicParticipants(data) {
        const counts = processCount(data, 'referring_clinic');
        const chartData = {
            labels: counts.map(d => d[0]),
            datasets: [{ data: counts.map(d => d[1]), backgroundColor: COLORS, borderColor: COLORS_BORDER, borderWidth: 1 }]
        };
        charts.clinicParticipants = new Chart(chartConfigs.clinicParticipants.ctx, { ...chartConfigs.clinicParticipants, data: chartData });
    }
});