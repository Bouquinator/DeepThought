"""Project-level checks. Each takes (ctx, suite, stage) and fills the StageState."""

from deepthought.checks import files, forbidden, make, norminette

CHECKS = {
    "rules": make.rules,
    "relink": make.relink,
    "norminette": norminette.check,
    "forbidden": forbidden.check,
    "files": files.check,
}

TITLES = {
    "rules": "Makefile rules",
    "relink": "No relink",
    "norminette": "Norminette",
    "forbidden": "Forbidden functions",
    "files": "Required files",
}
