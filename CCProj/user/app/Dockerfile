FROM python
EXPOSE 8080
WORKDIR /app
COPY . /app
COPY main_user.py /app 
RUN pip install -r requirements.txt
CMD python3 /app/main_user.py

