#!/bin/env bash
SCRIPTPATH="$( cd -- "$( dirname -- "$0" )" &> /dev/null && pwd )"
OLD_CWD=$(pwd)
cd $SCRIPTPATH

LAMBDA_LIST=(
    get_data
    post_data
    login
    register
)

chmod 644 $(find . -type f)
chmod 755 $(find . -type d)

for lambda in ${LAMBDA_LIST[@]}; do
    if [[ ! -f "./$lambda.py" ]]; then
        echo "$lambda.py does not exist yet"
        continue
    fi
    echo "Zipping $lambda"
    if [[ -f "./${lambda}.zip" ]]; then
        rm -f ./${lambda}.zip
    fi
    zip -r "./${lambda}.zip" ./common ./temp "./${lambda}.py"
done

chmod 644 $(find . -type f)

cd $OLD_CWD