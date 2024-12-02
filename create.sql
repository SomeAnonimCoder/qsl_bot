CREATE DATABASE TelegramBot;

USE TelegramBot;

CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    telegram_id BIGINT NOT NULL UNIQUE
);

CREATE TABLE Contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_with_id INT NOT NULL,
    timestamp_range VARCHAR(50) NOT NULL,
    location POINT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (contact_with_id) REFERENCES Users(id)
);

CREATE TABLE SWL (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_with_id INT NOT NULL,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (contact_with_id) REFERENCES Users(id)
);

CREATE TABLE Bands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    band_name VARCHAR(255) NOT NULL
);


