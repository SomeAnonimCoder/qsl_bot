CREATE DATABASE TelegramBot;

USE TelegramBot;

DROP TABLE SWL;
DROP TABLE Contacts;
DROP TABLE Users;


CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    telegram_id BIGINT NOT NULL UNIQUE
);

CREATE TABLE Contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_with_id INT NOT NULL,
    band_id INT,
    timestamp DATETIME NOT NULL,
    location POINT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (contact_with_id) REFERENCES Users(id)
);

CREATE TABLE SWL (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_with_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    location POINT NOT NULL,
    band_id INT,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (contact_with_id) REFERENCES Users(id)
);

CREATE TABLE Bands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    band_name VARCHAR(255) NOT NULL
);


insert into Users(username,telegram_id) 
    values
      ("Artem's Beacon - EK/R2GEO", -1);


INSERT INTO Bands(band_name)
  VALUES 
    ("14MHz/20m"),("7MHz/40m"),("27MHz/11m/CB"),("28MHz/10m"),("144 MHz/2m"),("433 MHz/70cm"),("other");
