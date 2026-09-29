import WorkflowContainer from "./workflow.js"

export default {
    defaultTheme: 'light',
    iconLinks: [{
        icon: 'github',
        href: 'https://github.com/SainsburyWellcomeCentre/aeon_vertigate',
        title: 'GitHub'
    }],
    start: () => {
        WorkflowContainer.init();
    }
}
