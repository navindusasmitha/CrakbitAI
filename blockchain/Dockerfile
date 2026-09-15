FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY crakbit_chain ./crakbit_chain
RUN pip install --no-cache-dir .
EXPOSE 9101
CMD ["crakchain", "node", "--genesis", "/runtime/genesis.json", "--key", "/runtime/node1/validator.json", "--data", "/data"]
