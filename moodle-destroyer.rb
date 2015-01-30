#!/usr/bin/env ruby

require 'csv'

if ARGV.length < 2
  puts "Usage: moodle-destroyer moodle-file grading-file [output-file]"
  puts "Please run this command in the directory where your CSV files are located."
  exit 1
end

moodle_export = ARGV[0]
grading_file  = ARGV[1]
result_file   = ARGV[2]

if result_file == nil
  result_file = "result.csv"
end

moodle_csv = CSV.read(moodle_export)

CSV.open(result_file, "wb") do |csv| 
  csv << moodle_csv[0]
  CSV.foreach(grading_file, headers: true) do |grading_row| 
    grading_row.to_hash.each do |grading_key, grading_value| 
      CSV.foreach(moodle_export, headers: true) do |row|
        row.to_hash.each do |key, value|
          if grading_value == value
            row['Bewertung'] = grading_row['Bewertung']
            row['Feedback als Kommentar'] = grading_row['Feedback als Kommentar']
            csv << row
          end
        end
      end
    end
  end
end

puts "Done... Please look into #{result_file}"

