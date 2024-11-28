#! /usr/bin/env bash

# Reads the .env file and sets the variables as secrets in fly environment

cat .env | fly secrets import
