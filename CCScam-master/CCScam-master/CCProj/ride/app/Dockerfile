FROM python
COPY . /ride
EXPOSE 80
WORKDIR /ride
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python","main_rides.py"] 
