FROM python
COPY . /user
EXPOSE 80
WORKDIR /user
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python","main_user.py"]
