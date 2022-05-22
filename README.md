# IUH LMS Recommendation System

## Setup environment

To start development, you need to create your own Python environment

If you haven't virtualenv installed, you can install it with the following command:

```bash
pip install virtualenv
```

Then, create a new virtual environment with the following command:

```bash
python -m virtualenv .venv
```

## Start Python virtual environment

- with MacOS or Linux

    ```bash
    .venv/bin/activate
    ```

- with Windows

    ```bash
    .venv\Scripts\activate
    ```

## Install dependencies

After the virtual environment is created, you can install the dependencies with the following command:

```bash
pip install -r requirements.txt
```

## Start a server

```bash
### chage directory to the Django project
cd deploy_ml

### call the manage.py
python manage.py runserver
```

Happy coding!
