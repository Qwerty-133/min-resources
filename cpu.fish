#!/usr/bin/fish
set sum 0
set samples 10
for i in (seq 1 $samples)
    set cpu_usage (
        top -bn1 | grep "Cpu(s)" |
        sed "s/.*, *\([0-9.]*\)%* id.*/\1/" |
        awk '{print 100 - $1""}'
    )
    set sum (math $sum + $cpu_usage)
end

echo (math $sum / $samples)
