FROM fission/python-env:3.9

# 安装 Chromium、Chromedriver 和依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install --no-cache-dir selenium elasticsearch

# 设置环境变量（供 Selenium 使用）
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
