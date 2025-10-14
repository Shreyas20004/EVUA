export const projectFiles = [
    { name: 'setup.py', status: 'upgraded' },
    { name: 'requirements.txt', status: 'upgraded' },
    { name: 'legacy/utils.py', status: 'needs-review' },
    { name: 'legacy/api/v1.py', status: 'needs-review' },
    { name: 'legacy/handlers.py', status: 'pending' },
    { name: 'tests/test_utils.py', status: 'upgraded' },
    { name: 'app/main.py', status: 'upgraded' }
];


export const codeDiff = {
    py2: `print \"Hello, world\"\nxrange(10)\ndict.iteritems()\nraise ValueError, \"Invalid\"\n\ndef f(x):\n print x`,
    py3: `print(\"Hello, world\")\nrange(10)\ndict.items()\nraise ValueError(\"Invalid\")\n\ndef f(x):\n print(x)`
};